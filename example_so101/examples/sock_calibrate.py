#!/usr/bin/env python3

"""
CALIBRATION TOOL

Workflow:
1. Robot moves to known pose
2. Camera opens
3. Move sock underneath end effector
4. Sock detector prints pixel coordinates
5. Record coordinates for calibration

Press:
- n = next calibration point
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
# REAL CAMERA WORKSPACE CALIBRATION
# ============================================================

CAM_X_MIN = 340
CAM_X_MAX = 400

CAM_Y_MIN = 94
CAM_Y_MAX = 340

# ============================================================
# CALIBRATED ROBOT CORNER POSES
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

# ============================================================
# HEIGHT CONTROL
# ============================================================

HOVER_OFFSET = 40

# ============================================================
# BILINEAR INTERPOLATION
# ============================================================

def interpolate_pose(pixel_x, pixel_y):

    u = (pixel_x - CAM_X_MIN) / (CAM_X_MAX - CAM_X_MIN)
    v = (pixel_y - CAM_Y_MIN) / (CAM_Y_MAX - CAM_Y_MIN)

    u = np.clip(u, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    pose = (
        (1-u)*(1-v)*farHigh +
        u*(1-v)*farLow +
        (1-u)*v*closeHigh +
        u*v*closeLow
    )

    pose[1] -= HOVER_OFFSET
    pose[2] += HOVER_OFFSET

    return pose

# ============================================================
# SOCK DETECTION
# ============================================================

def detect_sock(frame):

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5,5), 0)

    _, mask = cv2.threshold(
        blurred,
        60,
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
# TEST POINTS
# ============================================================

TEST_POINTS = [

    ("CENTER", 370, 220),

    ("TOP_LEFT", 340, 94),

    ("TOP_RIGHT", 400, 94),

    ("BOTTOM_LEFT", 340, 340),

    ("BOTTOM_RIGHT", 400, 340),

]

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("================================================")
    print("SO101 WORKSPACE CALIBRATION")
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

    print("\n✓ Robot enabled")

    # --------------------------------------------------------
    # Camera
    # --------------------------------------------------------

    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Could not open camera")
        exit()

    print("✓ Camera opened")

    time.sleep(2)

    # ========================================================
    # TEST LOOP
    # ========================================================

    for name, px, py in TEST_POINTS:

        print("\n================================================")
        print(f"Moving to: {name}")
        print(f"Expected pixel: ({px}, {py})")

        joints = interpolate_pose(px, py)

        print("\nTarget joints:")
        print(joints)

        robot.set_target_joint_angles(joints)

        # Allow robot to move
        time.sleep(3)

        print("\nMove sock under end effector.")
        print("Press 'n' for next point.")
        print("Press 'q' to quit.")

        # ----------------------------------------------------
        # Camera calibration loop
        # ----------------------------------------------------

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            frame = cv2.resize(frame, (640, 480))

            sock_x, sock_y, contour, mask = detect_sock(frame)

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
                    f"SOCK: ({sock_x}, {sock_y})",
                    (sock_x + 10, sock_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0,255,0),
                    2
                )

                print(f"\rDetected sock at: ({sock_x}, {sock_y})", end="")

            cv2.imshow("Calibration", frame)
            cv2.imshow("Sock Mask", mask)

            key = cv2.waitKey(1) & 0xFF

            # Next point
            if key == ord('n'):
                print("\nMoving to next point...")
                break

            # Quit
            if key == ord('q'):

                cap.release()
                cv2.destroyAllWindows()

                robot.cleanup()

                print("\nDone.")
                exit()

    # ========================================================
    # CLEANUP
    # ========================================================

    cap.release()
    cv2.destroyAllWindows()

    robot.cleanup()

    print("\nCalibration complete.")