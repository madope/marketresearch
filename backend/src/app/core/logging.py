from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings


_LOGGER_CONFIGURED = False
_LOG_PATH: Path | None = None


def configure_app_logging() -> Path:
    global _LOGGER_CONFIGURED, _LOG_PATH

    settings = get_settings()
    log_dir = Path(settings.app_log_dir)
    if not log_dir.is_absolute():
        log_dir = Path.cwd() / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "app.log"
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    stale_handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) != log_path
    ]
    for handler in stale_handlers:
        logger.removeHandler(handler)
        handler.close()

    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path for handler in logger.handlers):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)

    _LOGGER_CONFIGURED = True
    _LOG_PATH = log_path
    return log_path


def get_app_logger(name: str) -> logging.Logger:
    configure_app_logging()
    return logging.getLogger(f"app.{name}")
