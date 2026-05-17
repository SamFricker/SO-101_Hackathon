"""Pluggable humidity readers for environment logging."""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any


class HumiditySource(ABC):
    """Read relative humidity as a percentage (0–100)."""

    @abstractmethod
    def read_humidity_percent(self) -> float | None:
        """Return humidity in percent, or None if unavailable."""


class MockHumiditySource(HumiditySource):
    """Sinusoidal humidity for testing without hardware."""

    def __init__(self, base_percent: float = 45.0, amplitude: float = 5.0) -> None:
        self._base = base_percent
        self._amplitude = amplitude
        self._t0 = time.time()

    def read_humidity_percent(self) -> float | None:
        elapsed = time.time() - self._t0
        return self._base + self._amplitude * (0.5 + 0.5 * math.sin(elapsed / 10.0))


class HttpHumiditySource(HumiditySource):
    """Fetch humidity from a JSON HTTP endpoint."""

    def __init__(
        self,
        url: str,
        json_key: str = "humidity",
        timeout_s: float = 2.0,
    ) -> None:
        self._url = url
        self._json_key = json_key
        self._timeout_s = timeout_s

    def read_humidity_percent(self) -> float | None:
        try:
            request = urllib.request.Request(
                self._url,
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                payload: Any = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return None

        value = _extract_json_value(payload, self._json_key)
        if value is None:
            return None
        return float(value)


class SerialHumiditySource(HumiditySource):
    """Read one float per line from a serial port (e.g. Arduino sensor)."""

    def __init__(self, port: str, baudrate: int = 9600) -> None:
        import serial

        self._serial = serial.Serial(port, baudrate=baudrate, timeout=1.0)

    def read_humidity_percent(self) -> float | None:
        try:
            line = self._serial.readline().decode(errors="ignore").strip()
        except Exception:
            return None
        if not line:
            return None
        try:
            return float(line.split(",")[0])
        except ValueError:
            return None

    def close(self) -> None:
        if self._serial.is_open:
            self._serial.close()


class AtechSerialHumiditySource(HumiditySource):
    """Read humidity from an Atech motherboard over USB serial (115200 baud).

    Expects newline-delimited JSON events per https://atech.dev/docs, e.g.:
    {"type":"sensor","key":"humidity","value":65.2,"module_type":"aht20"}
    """

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        import serial

        self._serial = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        self._latest: float | None = None

    def read_humidity_percent(self) -> float | None:
        try:
            while self._serial.in_waiting:
                line = self._serial.readline().decode(errors="ignore")
                humidity = parse_atech_humidity_event(line)
                if humidity is not None:
                    self._latest = humidity
        except Exception:
            return self._latest
        return self._latest

    def close(self) -> None:
        if self._serial.is_open:
            self._serial.close()


def parse_atech_humidity_event(line: str) -> float | None:
    """Parse one Atech sensor JSON line; return humidity %RH if present."""
    line = line.strip()
    if not line or not line.startswith("{"):
        return None
    try:
        message: Any = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(message, dict):
        return None
    if message.get("type") != "sensor" or message.get("key") != "humidity":
        return None
    value = message.get("value")
    if value is None:
        return None
    return float(value)


def _extract_json_value(payload: Any, key: str) -> Any | None:
    """Support dotted paths such as 'sensors.humidity'."""
    current: Any = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def create_humidity_source(
    source: str,
    *,
    http_url: str = "",
    http_json_key: str = "humidity",
    serial_port: str = "",
    serial_baudrate: int = 115200,
) -> HumiditySource | None:
    """Factory for CLI-selected humidity backends."""
    if source == "none":
        return None
    if source == "mock":
        return MockHumiditySource()
    if source == "http":
        if not http_url:
            raise ValueError("--humidity-url is required when --humidity-source=http")
        return HttpHumiditySource(http_url, json_key=http_json_key)
    if source == "serial":
        if not serial_port:
            raise ValueError(
                "--humidity-serial-port is required when --humidity-source=serial"
            )
        return SerialHumiditySource(serial_port, baudrate=serial_baudrate)
    if source == "atech":
        if not serial_port:
            raise ValueError(
                "--humidity-serial-port is required when --humidity-source=atech "
                "(USB-C port of the Atech motherboard, e.g. COM6 on Windows)"
            )
        return AtechSerialHumiditySource(serial_port, baudrate=serial_baudrate)
    raise ValueError(f"Unknown humidity source: {source}")
