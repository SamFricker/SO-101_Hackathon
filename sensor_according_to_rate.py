import serial
import json
import time
import threading

PORT = "COM5"
SETTLE_SECONDS  = 5     # time to confirm sensor is back to neutral (no clothing)
MEASURE_SECONDS = 5     # time to measure clothing
TEMP_THRESHOLD  = 0.01  # °C/s
HUM_THRESHOLD   = 0.05  # %/s

lock = threading.Lock()

prev = {}

state          = "waiting"
phase_start    = None
phase_rates    = {"temperature": [], "humidity": []}
local_baseline = {}

def classify(avg_rate, threshold):
    if avg_rate > threshold:  return "positive"
    if avg_rate < -threshold: return "negative"
    return "ambient"

def get_status(t_class, h_class):
    hot = t_class == "positive"
    wet = h_class == "positive"
    if wet and hot:   return "Wet and hot 💧🔥"
    if wet and not hot: return "Wet and cold 💧🧊"
    if not wet and hot: return "Dry and hot 🌵🔥"
    return "Dry and cold 🌵🧊"

def read_serial():
    global state, phase_start, phase_rates, local_baseline

    ser = serial.Serial(PORT, 115200, timeout=2)
    print("Connected to COM5.")
    print("Press Enter to begin measuring a clothing item.\n", flush=True)

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

        if key not in ("temperature", "humidity"):
            continue

        now  = time.time()
        rate = None

        if key in prev:
            dt = now - prev[key]["time"]
            if dt > 0:
                rate = (value - prev[key]["value"]) / dt
        prev[key] = {"value": value, "time": now}

        with lock:
            if state == "waiting" or rate is None:
                continue

            elapsed   = now - phase_start
            remaining = (SETTLE_SECONDS if state == "settling" else MEASURE_SECONDS) - elapsed

            if state == "settling":
                local_baseline[key] = value
                print(f"  Settling... {remaining:.1f}s (ensure no clothing near sensor)", end="\r", flush=True)

                if elapsed >= SETTLE_SECONDS:
                    state       = "measuring"
                    phase_start = now
                    phase_rates = {"temperature": [], "humidity": []}
                    print(f"\nPlace clothing near sensor now — measuring for {MEASURE_SECONDS}s...", flush=True)

            elif state == "measuring":
                if key in local_baseline:
                    phase_rates[key].append(rate)

                print(f"  Measuring... {remaining:.1f}s left", end="\r", flush=True)

                if elapsed >= MEASURE_SECONDS:
                    t_rates = phase_rates["temperature"]
                    h_rates = phase_rates["humidity"]

                    if t_rates and h_rates:
                        t_avg   = sum(t_rates) / len(t_rates)
                        h_avg   = sum(h_rates) / len(h_rates)
                        t_class = classify(t_avg, TEMP_THRESHOLD)
                        h_class = classify(h_avg, HUM_THRESHOLD)
                        status  = get_status(t_class, h_class)

                        print(f"\n\nResult:", flush=True)
                        print(f"  Temp rate avg:     {t_avg:+.4f}°C/s", flush=True)
                        print(f"  Humidity rate avg: {h_avg:+.4f}%/s", flush=True)
                        print(f"  Classification:    {status}", flush=True)
                    else:
                        print("\nNot enough data — try again.", flush=True)

                    state = "waiting"
                    print(f"\nRemove clothing. Press Enter for next item...\n", flush=True)

thread = threading.Thread(target=read_serial, daemon=True)
thread.start()

def input_loop():
    global state, phase_start, phase_rates, local_baseline
    while True:
        input()
        with lock:
            if state == "waiting":
                state          = "settling"
                phase_start    = time.time()
                local_baseline = {}
                phase_rates    = {"temperature": [], "humidity": []}
                print(f"Settling for {SETTLE_SECONDS}s — keep sensor clear...", flush=True)

input_thread = threading.Thread(target=input_loop, daemon=True)
input_thread.start()

# Keep main thread alive
while True:
    time.sleep(1)
