import numpy as np
import time

# ============================================
# CALIBRATION
# ============================================

CAM_X_MIN = 100
CAM_X_MAX = 540

CAM_Y_MIN = 100
CAM_Y_MAX = 380

# Neutral "touching table" pose
HOME_POSE = np.array([
    -5.4,
    33.9,
    66.9,
    167.7,
    170.9
])

# ============================================
# JOINT LIMIT RANGES (empirical)
# Tune these slowly and carefully
# ============================================

BASE_LEFT = -40
BASE_RIGHT = 40

SHOULDER_FORWARD = 10
SHOULDER_BACK = 55

ELBOW_FORWARD = 40
ELBOW_BACK = 90

# Wrist stays mostly fixed downward
WRIST_1 = 167
WRIST_2 = 171

# ============================================
# CAMERA -> ROBOT MAPPING
# ============================================

def map_range(value, in_min, in_max, out_min, out_max):
    return np.interp(
        value,
        [in_min, in_max],
        [out_min, out_max]
    )

# ============================================
# SIMPLE TABLE IK
# ============================================

def move_to_table_xy(pixel_x, pixel_y):

    # ----------------------------
    # Base rotation from X
    # ----------------------------
    base = map_range(
        pixel_x,
        CAM_X_MIN,
        CAM_X_MAX,
        BASE_LEFT,
        BASE_RIGHT
    )

    # ----------------------------
    # Shoulder from Y
    # ----------------------------
    shoulder = map_range(
        pixel_y,
        CAM_Y_MIN,
        CAM_Y_MAX,
        SHOULDER_FORWARD,
        SHOULDER_BACK
    )

    # ----------------------------
    # Elbow compensates
    # ----------------------------
    elbow = map_range(
        pixel_y,
        CAM_Y_MIN,
        CAM_Y_MAX,
        ELBOW_FORWARD,
        ELBOW_BACK
    )

    joints = [
        base,
        shoulder,
        elbow,
        WRIST_1,
        WRIST_2
    ]

    return joints

# ============================================
# TEST
# ============================================

if __name__ == "__main__":

    test_x = 320
    test_y = 240

    joints = move_to_table_xy(test_x, test_y)

    print("Target joints:")
    print(joints)