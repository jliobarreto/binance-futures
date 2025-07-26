import logging
from utils.path import LOGS_DIR


def setup_logging(mode: str = "production") -> None:
    """Configure global logging with optional debug or production mode.

    In debug mode all messages are shown on the console and recorded in
    ``runtime.log``. Errors are also stored in ``audit.log`` for further
    inspection. In production mode only informational messages are printed to
    the console, while files keep full debug information.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    runtime_log = LOGS_DIR / "runtime.log"
    audit_log = LOGS_DIR / "audit.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    file_handler = logging.FileHandler(runtime_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    error_handler = logging.FileHandler(audit_log, encoding="utf-8")
    error_handler.setLevel(logging.INFO)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    if mode.lower() == "production":
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    root.handlers = [file_handler, error_handler, console_handler]
