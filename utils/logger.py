import logging
from pathlib import Path
from .path import LOGS_DIR


def setup_logging(mode: str = "production") -> None:
    """Configure root logger.

    Parameters
    ----------
    mode: str, optional
        Execution mode. "debug" enables verbose output.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "runtime.log"
    level = logging.DEBUG if mode == "debug" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
