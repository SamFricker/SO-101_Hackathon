import json
import time
import sys
from pathlib import Path

import numpy as np

# Add repo paths
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "examples"))

from common.configs import (
    NEUTRAL_JOINT_ANGLES,
    ROBOT_RATE,
)

from so101_controller import SO101Controller

# ============================================
# CONFIG
# ============================================

POSES_FILE = "poses.json"

MOVE_SPEED = 0.02
STEP_SIZE = 1.0

# Gripper values: swap these if your robot works the opposite way
GRIPPER_OPEN_VALUE = 1.0
GRIPPER_CLOSE_VALUE = 0.0

# Conservative safety limits
JOINT_LIMITS = [
    (-120, 120),
    (-90, 90),
    (40, 140),
    (-180, 180),
    (-180, 180),
]

# ============================================
# LOAD POSES
# ============================================

with open(POSES_FILE, "r") as f:
    poses = json.load(f)

# ============================================
# CONNECT ROBOT
# ============================================

robot = SO101Controller(
    port="COM5",
    follower_id="my_follower_arm",
    robot_rate=ROBOT_RATE,
    neutral_joint_angles=NEUTRAL_JOINT_ANGLES,
    debug_mode=False,
)

robot.start_control_loop()
robot.resume_robot()

time.sleep(2)

# ============================================
# SAFETY
# ============================================

def clamp_joints(joints):
    safe = []

    for i, angle in enumerate(joints):
        low, high = JOINT_LIMITS[i]
        safe.append(np.clip(angle, low, high))

    return np.array(safe)

def open_gripper():
    print("Opening gripper...")
    robot.set_gripper_open_value(GRIPPER_OPEN_VALUE)

def close_gripper():
    print("Closing gripper...")
    robot.set_gripper_open_value(GRIPPER_CLOSE_VALUE)

# ============================================
# SMOOTH MOTION
# ============================================

def move_to_pose(name):
    if name not in poses:
        print(f"Pose '{name}' not found")
        return

    target = np.array(poses[name])
    target = clamp_joints(target)
    current = robot.get_current_joint_angles()

    print(f"\nMoving to: {name}")
    print(target)

    steps = int(np.max(np.abs(target - current)) / STEP_SIZE)
    steps = max(steps, 1)

    for i in range(steps):
        alpha = (i + 1) / steps
        interp = current + alpha * (target - current)
        robot.set_target_joint_angles(interp)
        time.sleep(MOVE_SPEED)

# ============================================
# MAIN LOOP
# ============================================

print("\nControls:")
print("1 = sensor")
print("2 = left bin")
print("3 = right bin")
print("o = open gripper")
print("c = close gripper")
print("q = quit")

try:
    while True:
        cmd = input("\nCommand: ").strip().lower()

        if cmd == "1":
            move_to_pose("sensor")

        elif cmd == "2":
            move_to_pose("Lbin")

        elif cmd == "3":
            move_to_pose("Rbin")

        elif cmd == "o":
            open_gripper()

        elif cmd == "c":
            close_gripper()

        elif cmd == "q":
            break

except KeyboardInterrupt:
    print("\nEmergency stop.")

# ============================================
# CLEANUP
# ============================================

print("\nStopping robot...")
robot.cleanup()
print("Done.")