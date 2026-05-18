import time
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

print("Starting robot controller...")
robot.start_control_loop()

print("Resuming robot...")
robot.resume_robot()

# Give robot time to stabilize
time.sleep(2)

# ============================================
# READ CURRENT POSITION
# ============================================

current = robot.get_current_joint_angles()

print("Current joint angles:")
print(current)

# ============================================
# CREATE TARGET POSITION
# ============================================

target_joint_angles = current.copy()

# Move ONE joint slightly
target_joint_angles[4] += -20
robot.set_gripper_open_value(0.5)

print("Target joint angles:")
print(target_joint_angles)

# ============================================
# SEND MOVEMENT
# ============================================

print("Moving robot...")

robot.set_target_joint_angles(target_joint_angles)

# ============================================
# KEEP PROGRAM RUNNING
# ============================================

print("Robot active. Press Ctrl+C to stop.")

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping robot...")

# ============================================
# CLEANUP
# ============================================

robot.cleanup()

print("Done.")