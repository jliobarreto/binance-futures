import logging
from pathlib import Path
from .path import LOGS_DIR


def setup_logging(mode: str = "production") -> None:
    """Configure root and audit loggers.

    Parameters
    ----------
    mode: str, optional
        Execution mode. "debug" enables verbose output.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if mode == "debug" else logging.INFO

    runtime_file = LOGS_DIR / "runtime.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(runtime_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Configure dedicated audit logger
    audit_file = LOGS_DIR / "audit.log"
    audit_handler = logging.FileHandler(audit_file, encoding="utf-8")
    audit_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(level)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False


def get_audit_logger() -> logging.Logger:
    """Return the dedicated audit logger."""
    return logging.getLogger("audit")


__all__ = ["setup_logging", "get_audit_logger"]