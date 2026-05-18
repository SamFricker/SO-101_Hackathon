#!/usr/bin/env python3

import sys
import time
from pathlib import Path

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

# These are REAL measured pixels
# corresponding to the calibrated robot workspace

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

    # Normalize pixel coordinates
    u = (pixel_x - CAM_X_MIN) / (CAM_X_MAX - CAM_X_MIN)
    v = (pixel_y - CAM_Y_MIN) / (CAM_Y_MAX - CAM_Y_MIN)

    u = np.clip(u, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    # Bilinear interpolation
    pose = (
        (1-u)*(1-v)*farHigh +
        u*(1-v)*farLow +
        (1-u)*v*closeHigh +
        u*v*closeLow
    )

    # Hover above table
    pose[1] -= HOVER_OFFSET
    pose[2] += HOVER_OFFSET

    return pose

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

    time.sleep(2)

    # --------------------------------------------------------
    # TEST LOOP
    # --------------------------------------------------------

    for name, px, py in TEST_POINTS:

        print("\n================================================")
        print(f"Moving to: {name}")
        print(f"Camera pixel: ({px}, {py})")

        joints = interpolate_pose(px, py)

        print("\nTarget joints:")
        print(joints)

        robot.set_target_joint_angles(joints)

        time.sleep(2)

        current = robot.get_current_joint_angles()

        print("\nCurrent joints:")
        print(current)

        input("\nPress ENTER to continue...")

    print("\nCalibration complete.")

    robot.cleanup()