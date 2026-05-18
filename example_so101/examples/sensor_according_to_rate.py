import serial
import json
import time
import threading

PORT = "COM5"
BASELINE_SECONDS = 10   # one-time startup baseline
MEASURE_SECONDS  = 5    # time to measure clothing
HUM_THRESHOLD    = 0.05  # %/s

lock = threading.Lock()

prev        = {}
state       = "baseline"
phase_start = None
phase_rates = {"humidity": []}
baseline    = {}
last_result = None  # "Wet" or "Dry" — updated after each measurement

def get_result():
    """Return the most recent classification, or None if no measurement done yet."""
    return last_result

def classify(avg_rate, threshold):
    if avg_rate > threshold:  return "positive"
    if avg_rate < -threshold: return "negative"
    return "ambient"

def run_baseline(key, value, elapsed):
    global state
    baseline[key] = value
    print(f"  Baseline... {BASELINE_SECONDS - elapsed:.1f}s remaining", end="\r", flush=True)

    if elapsed >= BASELINE_SECONDS:
        state = "waiting"
        print(f"\nBaseline set. Press Enter to measure a clothing item.\n", flush=True)

def run_measurement(key, rate, elapsed):
    global state, last_result
    phase_rates[key].append(rate)
    print(f"  Measuring... {MEASURE_SECONDS - elapsed:.1f}s left", end="\r", flush=True)

    if elapsed >= MEASURE_SECONDS:
        h_rates = phase_rates["humidity"]

        if h_rates:
            h_avg     = sum(h_rates) / len(h_rates)
            h_class   = classify(h_avg, HUM_THRESHOLD)
            last_result = "Wet" if h_class == "positive" else "Dry"
            status    = f"{last_result} 💧" if last_result == "Wet" else f"{last_result} 🌵"

            print(f"\n\nResult:", flush=True)
            print(f"  Humidity rate avg: {h_avg:+.4f}%/s", flush=True)
            print(f"  Classification:    {status}", flush=True)
        else:
            print("\nNot enough data — try again.", flush=True)

        state = "waiting"
        print(f"\nRemove clothing. Press Enter for next item...\n", flush=True)

def read_serial():
    global state, phase_start

    ser = serial.Serial(PORT, 115200, timeout=2)
    print("Connected to COM5.")
    print(f"Reading baseline for {BASELINE_SECONDS}s — keep sensor clear...\n", flush=True)

    with lock:
        phase_start = time.time()

    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
            payload = msg.get("payload", {})
            if payload.get("event_type") != "sensor":
                continue
            key   = payload["key"]
            value = payload["value"]
        except (json.JSONDecodeError, KeyError):
            continue

        if key != "humidity":
            continue

        now  = time.time()
        rate = None

        if key in prev:
            dt = now - prev[key]["time"]
            if dt > 0:
                rate = (value - prev[key]["value"]) / dt
        prev[key] = {"value": value, "time": now}

        with lock:
            if rate is None or phase_start is None:
                continue

            elapsed = now - phase_start

            if state == "baseline":
                run_baseline(key, value, elapsed)
            elif state == "waiting":
                continue
            elif state == "measuring":
                run_measurement(key, rate, elapsed)

thread = threading.Thread(target=read_serial, daemon=True)
thread.start()

def input_loop():
    global state, phase_start, phase_rates
    while True:
        input()
        with lock:
            if state == "waiting":
                state       = "measuring"
                phase_start = time.time()
                phase_rates = {"humidity": []}
                print(f"Place clothing near sensor — measuring for {MEASURE_SECONDS}s...", flush=True)

input_thread = threading.Thread(target=input_loop, daemon=True)
input_thread.start()

# Keep main thread alive
while True:
    time.sleep(1)