"""Configuration loader for the project.

This module exposes configuration values from two sources:

* ``settings.json`` – static numeric/str parameters committed to the repo.
* Environment variables – usually provided via a local ``.env`` file.  The
  module uses :mod:`python-dotenv` to load them automatically.

Both sources are loaded at import time and their values are exported as module
level constants so they can be imported directly from ``config``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a ``.env`` file if present
load_dotenv()

# ---- Read ``settings.json`` -------------------------------------------------
_settings_path = Path(__file__).with_name("settings.json")
with _settings_path.open() as f:
    _SETTINGS = json.load(f)

# ---- Environment variables --------------------------------------------------
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- Export every key from settings.json as module-level constants -----------
globals().update(_SETTINGS)

# Allow overriding the fallback DXY symbol through environment variables.
DXY_ALT_SYMBOL = os.getenv("DXY_ALT_SYMBOL", _SETTINGS.get("DXY_ALT_SYMBOL", "DX-Y.NYB"))

__all__ = [
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    *_SETTINGS.keys(),
]
