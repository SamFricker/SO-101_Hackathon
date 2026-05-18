#!/usr/bin/env python3

"""
FINAL LAUNDRY SORTER

Workflow:
1. Detect sock
2. Move to sock
3. Close gripper
4. Move to sensor
5. Measure humidity
6. Move to correct bin
7. Wait for ENTER to repeat
8. q + ENTER exits

Controls:
- ENTER = run next cycle
- q + ENTER = quit
"""

import json
import time
import threading
import serial
import sys
from pathlib import Path

import cv2
import numpy as np

# ============================================================
# Repo setup
# ============================================================

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "examples"))

from common.configs import (
    NEUTRAL_JOINT_ANGLES,
    ROBOT_RATE,
)

from so101_controller import SO101Controller

# ============================================================
# ROBOT CONFIG
# ============================================================

PORT = "COM6"
FOLLOWER_ID = "my_follower_arm"

MOVE_SPEED = 0.02
STEP_SIZE = 1.0

# ============================================================
# SENSOR CONFIG
# ============================================================

SENSOR_PORT = "COM7"

BASELINE_SECONDS = 10
MEASURE_SECONDS = 10

HUM_THRESHOLD = -20

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
# OFFSETS
# ============================================================

# Raises the arm higher above the table
HOVER_OFFSET = 250

# Pushes farther outward
REACH_OFFSET = 250

# ============================================================
# FIXED POSES
# ============================================================

SENSOR_POSE = np.array([
    -5.846153846153846,
    66.94505494505495,
    54.37362637362637,
    167.86813186813185,
    -3.032967032967033
])

LEFT_BIN_POSE = np.array([
    -82.94505494505495,
    43.472527472527474,
    36.79120879120879,
    162.5054945054945,
    -3.208791208791209
])

RIGHT_BIN_POSE = np.array([
    88.48351648351648,
    35.120879120879124,
    39.956043956043956,
    162.32967032967034,
    -3.120879120879121
])

# ============================================================
# GLOBALS
# ============================================================

lock = threading.Lock()

sensor_state = "baseline"
phase_start = None
phase_rates = {"humidity": []}

baseline = {}

last_result = None

measurement_done = threading.Event()

# ============================================================
# ROBOT
# ============================================================

robot = SO101Controller(
    port=PORT,
    follower_id=FOLLOWER_ID,
    robot_rate=ROBOT_RATE,
    neutral_joint_angles=NEUTRAL_JOINT_ANGLES,
    debug_mode=False,
)

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

    # Hover above table
    interpolated[1] -= HOVER_OFFSET
    interpolated[2] += HOVER_OFFSET

    # Reach farther outward
    interpolated[1] += REACH_OFFSET
    interpolated[2] -= REACH_OFFSET

    return interpolated

# ============================================================
# MOTION
# ============================================================

def move_joints(target):

    current = robot.get_current_joint_angles()

    target = np.array(target)

    steps = int(np.max(np.abs(target - current)) / STEP_SIZE)
    steps = max(steps, 1)

    for i in range(steps):

        alpha = (i + 1) / steps

        interp = current + alpha * (target - current)

        robot.set_target_joint_angles(interp)

        time.sleep(MOVE_SPEED)

def open_gripper():

    robot.set_gripper_open_value(0.5)

def close_gripper():

    robot.set_gripper_open_value(0.0)

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

            return center_x, center_y

    return None, None

# ============================================================
# SENSOR LOGIC
# ============================================================

def classify(avg_rate, threshold):

    if avg_rate > threshold:
        return "positive"

    if avg_rate < -threshold:
        return "negative"

    return "ambient"

# ============================================================
# SENSOR THREAD
# ============================================================

def sensor_reader():

    global sensor_state
    global phase_start
    global last_result

    ser = serial.Serial(SENSOR_PORT, 115200, timeout=2)

    print(f"Connected to {SENSOR_PORT}")

    with lock:

        phase_start = time.time()
        sensor_state = "baseline"

    prev = {}

    while True:

        line = ser.readline().decode(errors="ignore").strip()

        if not line:
            continue

        try:

            msg = json.loads(line)

            payload = msg.get("payload", {})

            if payload.get("event_type") != "sensor":
                continue

            key = payload["key"]
            value = payload["value"]

        except:
            continue

        if key != "humidity":
            continue

        now = time.time()

        rate = None

        if key in prev:

            dt = now - prev[key]["time"]

            if dt > 0:
                rate = (value - prev[key]["value"]) / dt

        prev[key] = {
            "value": value,
            "time": now
        }

        with lock:

            if phase_start is None or rate is None:
                continue

            elapsed = now - phase_start

            if sensor_state == "baseline":

                baseline[key] = value

                if elapsed >= BASELINE_SECONDS:

                    sensor_state = "waiting"

                    print("Baseline complete")

            elif sensor_state == "measuring":

                phase_rates[key].append(rate)

                if elapsed >= MEASURE_SECONDS:

                    h_rates = phase_rates["humidity"]

                    if h_rates:

                        h_avg = sum(h_rates) / len(h_rates)

                        h_class = classify(
                            h_avg,
                            HUM_THRESHOLD
                        )

                        last_result = (
                            "Wet"
                            if h_class == "positive"
                            else "Dry"
                        )

                        print(f"Result: {last_result}")

                    else:

                        last_result = None

                    sensor_state = "waiting"

                    measurement_done.set()

# ============================================================
# START MEASUREMENT
# ============================================================

def start_measurement():

    global sensor_state
    global phase_start
    global phase_rates

    with lock:

        phase_start = time.time()

        phase_rates = {
            "humidity": []
        }

        measurement_done.clear()

        sensor_state = "measuring"

# ============================================================
# START SYSTEMS
# ============================================================

sensor_thread = threading.Thread(
    target=sensor_reader,
    daemon=True
)

sensor_thread.start()

print("Starting robot...")

robot.start_control_loop()
robot.resume_robot()

open_gripper()

time.sleep(2)

print("Running baseline...")

while True:

    with lock:

        if sensor_state == "waiting":
            break

    time.sleep(0.1)

print("Baseline complete")

# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Could not open camera")
    exit()

# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        print("\n================================================")
        print("Place sock in scene.")
        print("Press ENTER to start.")
        print("Type q then ENTER to quit.")
        print("================================================")

        cmd = input().strip().lower()

        if cmd == "q":
            break

        # ----------------------------------------------------
        # Detect sock
        # ----------------------------------------------------

        sock_x = None
        sock_y = None

        print("Detecting sock...")

        while sock_x is None:

            ret, frame = cap.read()

            if not ret:
                continue

            frame = cv2.resize(frame, (640, 480))

            sock_x, sock_y = detect_sock(frame)

            cv2.imshow("Camera", frame)

            cv2.waitKey(1)

        print(f"Sock detected at: {sock_x}, {sock_y}")

        # ----------------------------------------------------
        # Open gripper
        # ----------------------------------------------------

        open_gripper()

        time.sleep(1)

        # ----------------------------------------------------
        # Move to sock
        # ----------------------------------------------------

        target_pose = interpolate_pose(
            sock_x,
            sock_y
        )

        print("Moving to sock...")

        move_joints(target_pose)

        # ----------------------------------------------------
        # Close gripper
        # ----------------------------------------------------

        print("Closing gripper...")

        close_gripper()

        time.sleep(1)

        # ----------------------------------------------------
        # Move to sensor
        # ----------------------------------------------------

        print("Moving to sensor...")

        move_joints(SENSOR_POSE)

        # ----------------------------------------------------
        # Measure
        # ----------------------------------------------------

        print("Starting humidity measurement...")

        start_measurement()

        measurement_done.wait()

        # ----------------------------------------------------
        # Choose bin
        # ----------------------------------------------------

        if last_result == "Wet":

            print("Moving to LEFT BIN")

            move_joints(LEFT_BIN_POSE)

        else:

            print("Moving to RIGHT BIN")

            move_joints(RIGHT_BIN_POSE)

        # ----------------------------------------------------
        # Release sock
        # ----------------------------------------------------

        open_gripper()

        time.sleep(1)

        print("Cycle complete.")

finally:

    cap.release()

    cv2.destroyAllWindows()

    robot.cleanup()

    print("Done.")