import serial
import json
import time

PORT = "COM5"
BASELINE_SECONDS = 15

ser = serial.Serial(PORT, 115200, timeout=2)
print(f"Connected to {PORT}. Collecting baseline for {BASELINE_SECONDS}s...\n")

baseline_samples = {"temperature": [], "humidity": []}
baseline = {}
start = time.time()

while True:
    line = ser.readline().decode(errors='ignore').strip()
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

    if key not in ("temperature", "humidity"):
        continue

    # Baseline collection phase
    if not baseline:
        elapsed = time.time() - start
        remaining = BASELINE_SECONDS - elapsed
        if remaining > 0:
            if value != 0.0:  # ignore sensor init zeroes
                baseline_samples[key].append(value)
            print(f"  Baseline ({remaining:.0f}s left) — {key}: {value:.1f}", end="\r", flush=True)
            continue
        else:
            # Compute baseline averages
            for k, samples in baseline_samples.items():
                baseline[k] = sum(samples) / len(samples) if samples else 0.0
            print(f"\nBaseline set — Temp: {baseline['temperature']:.1f}°C  |  Humidity: {baseline['humidity']:.1f}%\n", flush=True)
            print(f"{'Reading':<12} {'Current':>10} {'Baseline':>10} {'Difference':>12}", flush=True)
            print("-" * 48, flush=True)

    # Live diff phase
    diff = value - baseline.get(key, value)
    sign = "+" if diff >= 0 else ""
    if key == "temperature":
        print(f"{'Temperature':<12} {value:>9.1f}°C {baseline['temperature']:>9.1f}°C {sign}{diff:>10.1f}°C", flush=True)
    elif key == "humidity":
        print(f"{'Humidity':<12} {value:>10.1f}% {baseline['humidity']:>10.1f}% {sign}{diff:>11.1f}%", flush=True)
