from __future__ import annotations
import logging, os
from pathlib import Path
from logging.handlers import RotatingFileHandler

_LOG_DIR = Path("output") / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging(mode: str = "production") -> None:
    level = logging.DEBUG if mode.lower() == "development" else logging.INFO
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # root logger
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)

    # archivo rotativo
    file_handler = RotatingFileHandler(_LOG_DIR / "app.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))
    logging.getLogger().addHandler(file_handler)

def get_audit_logger() -> logging.Logger:
    logger = logging.getLogger("audit")
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        fmt = "%(asctime)s | %(levelname)s | %(message)s"
        handler = RotatingFileHandler(_LOG_DIR / "audit.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S"))
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger
