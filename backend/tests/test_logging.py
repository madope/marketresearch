from pathlib import Path

from app.core.logging import configure_app_logging, get_app_logger


def test_configure_app_logging_creates_log_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_LOG_DIR", str(tmp_path))

    log_path = configure_app_logging()

    assert log_path.exists()
    assert log_path.name == "app.log"


def test_app_logger_writes_message_to_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_LOG_DIR", str(tmp_path))
    log_path = configure_app_logging()
    logger = get_app_logger("test.logger")

    logger.info("workflow event test")

    assert "workflow event test" in log_path.read_text(encoding="utf-8")
