import json
import sys
from pathlib import Path

# Add repo paths
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "examples"))

from common.configs import (
    NEUTRAL_JOINT_ANGLES,
    ROBOT_RATE,
)

from so101_controller import SO101Controller

POSES_FILE = "poses.json"

# ============================================
# CONNECT ROBOT
# ============================================

robot = SO101Controller(
    port="COM6",
    follower_id="my_follower_arm",
    robot_rate=ROBOT_RATE,
    neutral_joint_angles=NEUTRAL_JOINT_ANGLES,
    debug_mode=False,
)

# ============================================
# DISABLE TORQUE
# ============================================

print("Disabling torque...")

for info in robot._robot._calibration.values():
    motor_id = info["id"]

    robot._robot._write_1byte(
        motor_id,
        40,   # ADDR_TORQUE_ENABLE
        0
    )

print("Torque disabled.")

# ============================================
# LOAD EXISTING POSES
# ============================================

try:
    with open(POSES_FILE, "r") as f:
        poses = json.load(f)
except:
    poses = {}

# ============================================
# MAIN LOOP
# ============================================

print("\nControls:")
print("Move robot arm by hand")
print("s = save pose")
print("q = quit")

try:

    while True:

        command = input("\nCommand: ")

        if command == "s":

            pose_name = input("Pose name: ")

            current = robot.get_current_joint_angles()

            poses[pose_name] = current.tolist()

            with open(POSES_FILE, "w") as f:
                json.dump(poses, f, indent=2)

            print(f"\nSaved pose '{pose_name}'")
            print(current)

        elif command == "q":
            break

except KeyboardInterrupt:
    pass

# ============================================
# CLEANUP
# ============================================

print("\nCleaning up...")

robot.cleanup()

print("Done.")