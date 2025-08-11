from __future__ import annotations
import json, os
from pathlib import Path

# Opcional: .env
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    pass

# Paths
ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "config" / "settings.json"

# Cargar settings.json
if not SETTINGS_PATH.exists():
    raise FileNotFoundError(f"No se encontró {SETTINGS_PATH}")
with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
    _S = json.load(f)

# ---- Requeridos de Telegram (desde .env)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- Parámetros (con defaults sanos)
MIN_SCORE_ALERTA     = int(_S.get("MIN_SCORE_ALERTA", 70))
VOLUMEN_MINIMO_USDT  = float(_S.get("VOLUMEN_MINIMO_USDT", 75_000_000))

ATR_SL_MULT          = float(_S.get("ATR_SL_MULT", 1.8))
TP_R_MULT            = float(_S.get("TP_R_MULT", 2.0))
SWING_LOOKBACK       = int(_S.get("SWING_LOOKBACK", 14))
MAX_ATR_PCT          = _S.get("MAX_ATR_PCT", None)

TIMEFRAMES           = _S.get("TIMEFRAMES", ["1d", "1w"])
LOOKBACK             = int(_S.get("LOOKBACK", 400))

SEND_TOP_N           = int(_S.get("SEND_TOP_N", 10))
COOLDOWN_MINUTES     = int(_S.get("COOLDOWN_MINUTES", 15))

EXCLUDE_SYMBOLS      = list(_S.get("EXCLUDE_SYMBOLS", []))
GRIDS_GAP_PCT        = float(_S.get("GRIDS_GAP_PCT", 0.024))

RSI_BUY_MIN          = float(_S.get("RSI_BUY_MIN", 40))
RSI_BUY_MAX          = float(_S.get("RSI_BUY_MAX", 55))
RSI_OVERSOLD         = float(_S.get("RSI_OVERSOLD", 30))
RSI_OVERBOUGHT       = float(_S.get("RSI_OVERBOUGHT", 70))
RSI_WEEKLY_OVERBOUGHT= float(_S.get("RSI_WEEKLY_OVERBOUGHT", 60))

MAX_CONSEC_LOSSES    = int(_S.get("MAX_CONSEC_LOSSES", 3))
BTC_DROP_THRESHOLD   = float(_S.get("BTC_DROP_THRESHOLD", 0.03))
VOLUME_DROP_THRESHOLD= float(_S.get("VOLUME_DROP_THRESHOLD", 0.3))

TRADE_HISTORY_FILE   = str(_S.get("TRADE_HISTORY_FILE", "data/trade_history.csv"))
DXY_ALT_SYMBOL       = str(_S.get("DXY_ALT_SYMBOL", "DX-Y.NYB"))

# ---- Fail-fast mínimo
_missing = []
if not TELEGRAM_TOKEN: _missing.append("TELEGRAM_TOKEN (.env)")
if not TELEGRAM_CHAT_ID: _missing.append("TELEGRAM_CHAT_ID (.env)")
if _missing:
    import logging
    logging.warning(
        "Faltan variables: %s (continuo; el envío a Telegram quedará desactivado)",
        ", ".join(_missing),
    )
