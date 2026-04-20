import json
import logging

from src.platform.logging import configure_logging, get_logger


def test_logger_emits_json_with_required_keys(caplog):
    configure_logging(level="INFO")
    log = get_logger("test")

    with caplog.at_level(logging.INFO):
        log.info("boot", component="platform", version="0.1.0-alpha.1")

    assert caplog.records, "expected at least one log record"
    record = caplog.records[-1]
    payload = json.loads(record.getMessage())
    assert payload["event"] == "boot"
    assert payload["component"] == "platform"
    assert payload["version"] == "0.1.0-alpha.1"
    assert payload["level"] == "info"
    assert "timestamp" in payload
