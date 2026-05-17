"""Camera threads - capture RGB images from USB webcams (OpenCV)."""

import time
import traceback
from collections.abc import Callable

import cv2
import numpy as np

from common.configs import (
    CAMERA_DEVICE_INDEX,
    CAMERA_FRAME_STREAMING_RATE,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    OVERHEAD_CAMERA_DEVICE_INDEX,
    OVERHEAD_CAMERA_HEIGHT,
    OVERHEAD_CAMERA_ROTATE_180,
    OVERHEAD_CAMERA_WIDTH,
)
from common.data_manager import DataManager


def rgb_camera_thread(
    data_manager: DataManager,
    *,
    device_index: int,
    frame_rate_hz: float,
    width: int,
    height: int,
    on_frame: Callable[[np.ndarray], None],
    label: str,
    rotate_180: bool = False,
) -> None:
    """Capture RGB frames from a USB webcam and push them via on_frame."""
    print(f"📷 Camera thread started ({label}, device {device_index})")

    dt = 1.0 / frame_rate_hz
    cap: cv2.VideoCapture | None = None

    try:
        cap = cv2.VideoCapture(device_index)
        if not cap.isOpened():
            print(
                f"❌ Could not open USB webcam '{label}' "
                f"(device index {device_index}). Check connection."
            )
            data_manager.request_shutdown()
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, frame_rate_hz)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  {label}: {actual_w}x{actual_h} @ ~{frame_rate_hz:.1f} Hz")

        while not data_manager.is_shutdown_requested():
            iteration_start = time.time()

            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"⚠️  Webcam read failed ({label}), skipping frame")
                time.sleep(dt)
                continue

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if rotate_180:
                rgb_image = cv2.rotate(rgb_image, cv2.ROTATE_180)
            on_frame(rgb_image)

            elapsed = time.time() - iteration_start
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        print(f"❌ Camera thread error ({label}): {e}")
        traceback.print_exc()
        data_manager.request_shutdown()
    finally:
        if cap is not None:
            cap.release()
            print(f"  ✓ USB webcam released ({label})")
        print(f"📷 Camera thread stopped ({label})")


def camera_thread(data_manager: DataManager) -> None:
    """Wrist/workspace camera (legacy entry point)."""
    rgb_camera_thread(
        data_manager,
        device_index=CAMERA_DEVICE_INDEX,
        frame_rate_hz=CAMERA_FRAME_STREAMING_RATE,
        width=CAMERA_WIDTH,
        height=CAMERA_HEIGHT,
        on_frame=data_manager.set_rgb_image,
        label="wrist",
        rotate_180=True,
    )


def overhead_camera_thread(data_manager: DataManager) -> None:
    """Overhead / scene camera above the workspace."""
    rgb_camera_thread(
        data_manager,
        device_index=OVERHEAD_CAMERA_DEVICE_INDEX,
        frame_rate_hz=CAMERA_FRAME_STREAMING_RATE,
        width=OVERHEAD_CAMERA_WIDTH,
        height=OVERHEAD_CAMERA_HEIGHT,
        on_frame=data_manager.set_overhead_rgb_image,
        label="overhead",
        rotate_180=OVERHEAD_CAMERA_ROTATE_180,
    )
