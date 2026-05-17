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
latest = {}

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
            if value != 0.0:
                baseline_samples[key].append(value)
            print(f"  Baseline ({remaining:.0f}s left) — {key}: {value:.1f}", end="\r", flush=True)
            continue
        else:
            for k, samples in baseline_samples.items():
                baseline[k] = sum(samples) / len(samples) if samples else 0.0
            print(f"\nBaseline set — Temp: {baseline['temperature']:.1f}°C  |  Humidity: {baseline['humidity']:.1f}%\n", flush=True)

    # Store latest diff
    diff = value - baseline.get(key, value)
    if key == "temperature":
        latest["temp_diff"] = diff
        latest["temp_label"] = "ambient" if diff == 0 else ("hot" if diff > 0 else "cold")
        latest["temp_sign"] = "+" if diff >= 0 else "-"
    elif key == "humidity":
        latest["hum_diff"] = diff
        latest["hum_label"] = "ambient" if diff == 0 else ("wet" if diff > 0 else "dry")
        latest["hum_sign"] = "+" if diff >= 0 else "-"

    # Print once both values are available
    if all(k in latest for k in ("temp_diff", "hum_diff")):
        t_sign, t_diff, t_label = latest["temp_sign"], abs(latest["temp_diff"]), latest["temp_label"]
        h_sign, h_diff, h_label = latest["hum_sign"], abs(latest["hum_diff"]), latest["hum_label"]

        print(f"Temp: {t_sign}{t_diff:.1f}°C ({t_label})  |  Humidity: {h_sign}{h_diff:.1f}% ({h_label})", flush=True)

        if t_label == "ambient" and h_label == "ambient":
            status = "Ambient 🌡️💧"
        elif h_label == "wet" and t_label == "hot":
            status = "Wet and hot 💧🔥"
        elif h_label == "wet" and t_label == "cold":
            status = "Wet and cold 💧🧊"
        elif h_label == "dry" and t_label == "hot":
            status = "Dry and hot 🌵🔥"
        elif h_label == "dry" and t_label == "cold":
            status = "Dry and cold 🌵🧊"
        else:
            status = f"{t_label.capitalize()} and {h_label} 🌡️"

        print(f"Status: {status}\n", flush=True)
