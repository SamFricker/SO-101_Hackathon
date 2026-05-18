#!/usr/bin/env python3

"""
FINAL MOVE TO SOCK

Uses:
- REAL measured calibration points
- Weighted interpolation
- Direct sock detection
- Radial reach extension

Controls:
- m = move robot to sock
- q = quit
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ============================================================
# Repo setup
# ============================================================

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "examples"))

from so101_controller import SO101Controller
from common.configs import (
    NEUTRAL_JOINT_ANGLES,
    ROBOT_RATE,
)

# ============================================================
# CALIBRATED ROBOT POSES
# ============================================================

closeLow = np.array([
    44.0,
    75.73626373626374,
    38.02197802197802,
    125.31868131868131,
    -4.175824175824176
])

farLow = np.array([
    15.252747252747254,
    148.17582417582418,
    -67.2967032967033,
    117.4065934065934,
    -4.263736263736264
])

farHigh = np.array([
    -45.23076923076923,
    147.82417582417582,
    -67.2967032967033,
    117.31868131868131,
    -4.263736263736264
])

closeHigh = np.array([
    -43.73626373626374,
    35.20879120879121,
    82.68131868131869,
    121.8021978021978,
    -4.263736263736264
])

centerPose = np.array([
    -7.24417046,
    60.60787992,
    38.08415974,
    120.53712142,
    -4.24122219
])

# ============================================================
# REAL CALIBRATION POINTS
# ============================================================

CALIBRATION = [

    {
        "pixel": np.array([267, 271]),
        "pose": centerPose
    },

    {
        "pixel": np.array([362, 59]),
        "pose": farHigh
    },

    {
        "pixel": np.array([367, 427]),
        "pose": farLow
    },

    {
        "pixel": np.array([120, 227]),
        "pose": closeHigh
    },

    {
        "pixel": np.array([145, 398]),
        "pose": closeLow
    }

]

# ============================================================
# HEIGHT + REACH
# ============================================================

HOVER_OFFSET = 230
REACH_OFFSET = 250

# ============================================================
# INTERPOLATION
# ============================================================

def interpolate_pose(pixel_x, pixel_y):

    target = np.array([pixel_x, pixel_y])

    weights = []
    poses = []

    for point in CALIBRATION:

        p = point["pixel"]
        pose = point["pose"]

        dist = np.linalg.norm(target - p)

        dist = max(dist, 1e-6)

        weight = 1.0 / dist

        weights.append(weight)
        poses.append(pose)

    weights = np.array(weights)
    weights /= np.sum(weights)

    interpolated = np.zeros(5)

    for w, pose in zip(weights, poses):
        interpolated += w * pose

    # --------------------------------------------------------
    # Hover above table
    # --------------------------------------------------------

    interpolated[1] -= HOVER_OFFSET
    interpolated[2] += HOVER_OFFSET

    # --------------------------------------------------------
    # Extend slightly farther outward
    # --------------------------------------------------------

    interpolated[1] += REACH_OFFSET
    interpolated[2] -= REACH_OFFSET

    return interpolated

# ============================================================
# SOCK DETECTION
# ============================================================

def detect_sock(frame):

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5,5), 0)

    _, mask = cv2.threshold(
        blurred,
        80,
        255,
        cv2.THRESH_BINARY_INV
    )

    kernel = np.ones((5,5), np.uint8)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if contours:

        largest = max(contours, key=cv2.contourArea)

        area = cv2.contourArea(largest)

        if area > 5000:

            x, y, w, h = cv2.boundingRect(largest)

            center_x = x + w // 2
            center_y = y + h // 2

            return center_x, center_y, largest, mask

    return None, None, None, mask

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("================================================")
    print("FINAL MOVE TO SOCK")
    print("================================================")

    # --------------------------------------------------------
    # Robot
    # --------------------------------------------------------

    robot = SO101Controller(
        port="COM6",
        follower_id="my_follower_arm",
        robot_rate=ROBOT_RATE,
        neutral_joint_angles=NEUTRAL_JOINT_ANGLES,
        debug_mode=False,
    )

    robot.start_control_loop()
    robot.resume_robot()

    print("✓ Robot enabled")

    # --------------------------------------------------------
    # Camera
    # --------------------------------------------------------

    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    if not cap.isOpened():

        print("Camera 1 failed, trying camera 0...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():

        print("Camera 0 failed, trying camera 2...")
        cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Could not open camera")
        exit()

    print("✓ Camera opened")

    cv2.namedWindow("Sock Detection", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Sock Mask", cv2.WINDOW_NORMAL)

    time.sleep(2)

    print("Entering camera loop...")

    # ========================================================
    # MAIN LOOP
    # ========================================================

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame")
            continue

        frame = cv2.resize(frame, (640, 480))

        sock_x, sock_y, contour, mask = detect_sock(frame)

        # ----------------------------------------------------
        # Draw sock
        # ----------------------------------------------------

        if sock_x is not None:

            cv2.drawContours(
                frame,
                [contour],
                -1,
                (0,255,0),
                2
            )

            cv2.circle(
                frame,
                (sock_x, sock_y),
                8,
                (0,0,255),
                -1
            )

            cv2.putText(
                frame,
                f"Sock ({sock_x},{sock_y})",
                (sock_x + 10, sock_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0,255,0),
                2
            )

        # ----------------------------------------------------
        # Show windows
        # ----------------------------------------------------

        cv2.imshow("Sock Detection", frame)
        cv2.imshow("Sock Mask", mask)

        key = cv2.waitKey(1) & 0xFF

        # ----------------------------------------------------
        # Move robot
        # ----------------------------------------------------

        if key == ord('m'):

            if sock_x is not None:

                print("\nMoving to sock...")

                joints = interpolate_pose(
                    sock_x,
                    sock_y
                )

                print("Sock coordinates:")
                print(sock_x, sock_y)

                print("Joint targets:")
                print(joints)

                robot.set_target_joint_angles(joints)

                print("COMMAND SENT")

                time.sleep(2)

            else:

                print("No sock detected")

        # ----------------------------------------------------
        # Quit
        # ----------------------------------------------------

        if key == ord('q'):
            break

    # ========================================================
    # CLEANUP
    # ========================================================

    cap.release()
    cv2.destroyAllWindows()

    robot.cleanup()

    print("Done.")