#1 Detect where the sock is and move there, maybe sensor can simultaneously run baseline?
#close gripper
#Move sock to the sensor
#sensor detects and passes signal
#robot determines to place sock in bin 1 or bin 2
#!/usr/bin/env python3
import json
import time
import threading
import serial
import sys
from pathlib import Path
import numpy as np

# Add repo paths
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "examples"))

from common.configs import NEUTRAL_JOINT_ANGLES, ROBOT_RATE
from so101_controller import SO101Controller

# -----------------------------
# ROBOT CONFIG
# -----------------------------
PORT = "COM5"
FOLLOWER_ID = "my_follower_arm"
POSES_FILE = "poses.json"

MOVE_SPEED = 0.02
STEP_SIZE = 1.0
JOINT_LIMITS = [
    (-120, 120),
    (-90, 90),
    (40, 140),
    (-180, 180),
    (-180, 180),
]

# -----------------------------
# SENSOR CONFIG
# -----------------------------
SENSOR_PORT = "COM6"
BASELINE_SECONDS = 10
MEASURE_SECONDS = 5
HUM_THRESHOLD = 0.05

lock = threading.Lock()
sensor_state = "baseline"
phase_start = None
phase_rates = {"humidity": []}
baseline = {}
last_result = None   # "Wet" / "Dry"
measurement_done = threading.Event()

def classify(avg_rate, threshold):
    if avg_rate > threshold:
        return "positive"
    if avg_rate < -threshold:
        return "negative"
    return "ambient"

def clamp_joints(joints):
    safe = []
    for i, angle in enumerate(joints):
        low, high = JOINT_LIMITS[i]
        safe.append(np.clip(angle, low, high))
    return np.array(safe)

def load_poses():
    with open(POSES_FILE, "r") as f:
        return json.load(f)

poses = load_poses()

robot = SO101Controller(
    port=PORT,
    follower_id=FOLLOWER_ID,
    robot_rate=ROBOT_RATE,
    neutral_joint_angles=NEUTRAL_JOINT_ANGLES,
    debug_mode=False,
)

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

def open_gripper():
    robot.set_gripper_open_value(1.0)

def close_gripper():
    robot.set_gripper_open_value(0.0)

def sensor_reader():
    global sensor_state, phase_start, last_result

    ser = serial.Serial(SENSOR_PORT, 115200, timeout=2)
    print(f"Connected to {SENSOR_PORT}.")

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
        except (json.JSONDecodeError, KeyError):
            continue

        if key != "humidity":
            continue

        now = time.time()
        rate = None

        if key in prev:
            dt = now - prev[key]["time"]
            if dt > 0:
                rate = (value - prev[key]["value"]) / dt
        prev[key] = {"value": value, "time": now}

        with lock:
            if phase_start is None or rate is None:
                continue

            elapsed = now - phase_start

            if sensor_state == "baseline":
                baseline[key] = value
                print(f"  Baseline... {BASELINE_SECONDS - elapsed:.1f}s remaining", end="\r", flush=True)
                if elapsed >= BASELINE_SECONDS:
                    sensor_state = "waiting"
                    print("\nBaseline set.")

            elif sensor_state == "measuring":
                phase_rates[key].append(rate)
                print(f"  Measuring... {MEASURE_SECONDS - elapsed:.1f}s left", end="\r", flush=True)

                if elapsed >= MEASURE_SECONDS:
                    h_rates = phase_rates["humidity"]
                    if h_rates:
                        h_avg = sum(h_rates) / len(h_rates)
                        h_class = classify(h_avg, HUM_THRESHOLD)
                        last_result = "Wet" if h_class == "positive" else "Dry"
                        print(f"\nResult: {last_result}")
                    else:
                        last_result = None
                        print("\nNot enough data.")

                    sensor_state = "waiting"
                    measurement_done.set()

def start_measurement():
    global sensor_state, phase_start, phase_rates
    with lock:
        phase_start = time.time()
        phase_rates = {"humidity": []}
        measurement_done.clear()
        sensor_state = "measuring"

# -----------------------------
# MAIN
# -----------------------------
sensor_thread = threading.Thread(target=sensor_reader, daemon=True)
sensor_thread.start()

print("Starting robot controller...")
robot.start_control_loop()
robot.resume_robot()
time.sleep(2)

try:
    print("Baseline running. Keep sensor clear.")
    while True:
        with lock:
            if sensor_state == "waiting":
                break
        time.sleep(0.1)

    print("\nSequence starting...")

    # 1) Move to sock
    move_to_pose("sock")

    # 2) Close gripper
    close_gripper()
    time.sleep(1)

    # 3) Move to sensor
    move_to_pose("sensor")

    # 4) Start humidity measurement
    print("Starting humidity measurement...")
    start_measurement()
    measurement_done.wait()

    # 5) Choose bin
    if last_result == "Wet":
        move_to_pose("Lbin")
    else:
        move_to_pose("Rbin")

finally:
    robot.cleanup()
    print("Done.")