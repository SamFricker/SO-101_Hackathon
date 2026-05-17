"""Unit tests for humidity source helpers."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from common.humidity_source import (  # noqa: E402
    HttpHumiditySource,
    MockHumiditySource,
    _extract_json_value,
    create_humidity_source,
    parse_atech_humidity_event,
)


def test_mock_humidity_in_range() -> None:
    source = MockHumiditySource(base_percent=50.0, amplitude=10.0)
    value = source.read_humidity_percent()
    assert value is not None
    assert 40.0 <= value <= 60.0


def test_extract_json_dotted_key() -> None:
    payload = {"sensors": {"humidity": 62.5}}
    assert _extract_json_value(payload, "sensors.humidity") == 62.5


def test_http_humidity_source() -> None:
    payload = json.dumps({"humidity": 55.0}).encode()

    class FakeResponse:
        def read(self) -> bytes:
            return payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    source = HttpHumiditySource("http://example.com/humidity")
    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        assert source.read_humidity_percent() == 55.0


def test_create_humidity_source_mock() -> None:
    assert create_humidity_source("mock") is not None
    assert create_humidity_source("none") is None


def test_parse_atech_humidity_event() -> None:
    line = (
        '{"type":"sensor","key":"humidity","value":65.2,"module_type":"aht20"}'
    )
    assert parse_atech_humidity_event(line) == 65.2
    assert parse_atech_humidity_event('{"type":"sensor","key":"temperature","value":23.5}') is None
    assert parse_atech_humidity_event("not json") is None
