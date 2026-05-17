"""Humidity polling thread for external environment sensors."""

import time
import traceback

import numpy as np

from common.data_manager import DataManager
from common.humidity_source import HumiditySource


def humidity_thread(
    data_manager: DataManager,
    source: HumiditySource,
    rate_hz: float,
    label: str = "humidity",
) -> None:
    """Poll a humidity source and push readings into the DataManager."""
    print(f"💧 Humidity thread started ({label} @ {rate_hz:.1f} Hz)")

    dt = 1.0 / rate_hz
    consecutive_failures = 0

    try:
        while not data_manager.is_shutdown_requested():
            iteration_start = time.time()

            humidity = source.read_humidity_percent()
            if humidity is not None:
                data_manager.set_humidity_percent(float(humidity))
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures == 1 or consecutive_failures % 20 == 0:
                    print(f"⚠️  Humidity read failed ({label}); retrying...")

            elapsed = time.time() - iteration_start
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    except Exception as e:
        print(f"❌ Humidity thread error: {e}")
        traceback.print_exc()
        data_manager.request_shutdown()
    finally:
        close = getattr(source, "close", None)
        if callable(close):
            close()
        print("💧 Humidity thread stopped")
