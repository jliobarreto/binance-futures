# config/__init__.py
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict

# Opcional: .env
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    pass

# Paths
ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "config" / "settings.json"

def _load_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}")
    # utf-8-sig para tragarse BOM si lo hubiera
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        raise RuntimeError(f"El archivo de configuración está vacío: {path}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # Mensaje claro de línea/columna
        raise RuntimeError(f"JSON inválido en {path}: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"El JSON raíz debe ser un objeto/dict en {path}")
    return data

# Cargar settings.json con manejo de errores
_S: Dict[str, Any] = _load_settings(SETTINGS_PATH)

# ---- Requeridos de Telegram (desde .env)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- Parámetros (con defaults sanos)
# Nota: si existen en _S, los sobreescribimos; si no, usamos el default.
MIN_SCORE_ALERTA      = int(_S.get("MIN_SCORE_ALERTA", 70))
VOLUMEN_MINIMO_USDT   = float(_S.get("VOLUMEN_MINIMO_USDT", 75_000_000))

ATR_SL_MULT           = float(_S.get("ATR_SL_MULT", 1.8))
TP_R_MULT             = float(_S.get("TP_R_MULT", 2.0))
SWING_LOOKBACK        = int(_S.get("SWING_LOOKBACK", 14))
MAX_ATR_PCT           = _S.get("MAX_ATR_PCT", None)  # puede ser None o float
ADX_MIN               = float(_S.get("ADX_MIN", 12))  # <- antes no lo exponías

TIMEFRAMES            = list(_S.get("TIMEFRAMES", ["1d", "1w"]))
LOOKBACK              = int(_S.get("LOOKBACK", 400))

SEND_TOP_N            = int(_S.get("SEND_TOP_N", 10))
COOLDOWN_MINUTES      = int(_S.get("COOLDOWN_MINUTES", 15))

EXCLUDE_SYMBOLS       = list(_S.get("EXCLUDE_SYMBOLS", []))
GRIDS_GAP_PCT         = float(_S.get("GRIDS_GAP_PCT", 0.024))

RSI_BUY_MIN           = float(_S.get("RSI_BUY_MIN", 40))
RSI_BUY_MAX           = float(_S.get("RSI_BUY_MAX", 55))
RSI_OVERSOLD          = float(_S.get("RSI_OVERSOLD", 30))
RSI_OVERBOUGHT        = float(_S.get("RSI_OVERBOUGHT", 70))
RSI_WEEKLY_OVERBOUGHT = float(_S.get("RSI_WEEKLY_OVERBOUGHT", 60))

MAX_CONSEC_LOSSES     = int(_S.get("MAX_CONSEC_LOSSES", 3))
BTC_DROP_THRESHOLD    = float(_S.get("BTC_DROP_THRESHOLD", 0.03))
VOLUME_DROP_THRESHOLD = float(_S.get("VOLUME_DROP_THRESHOLD", 0.3))

TRADE_HISTORY_FILE    = str(_S.get("TRADE_HISTORY_FILE", "data/trade_history.csv"))
DXY_ALT_SYMBOL        = str(_S.get("DXY_ALT_SYMBOL", "DX-Y.NYB"))

# Filtros de régimen/macro (antes tampoco quedaban expuestos)
USE_GLOBAL_TREND_FILTER = bool(_S.get("USE_GLOBAL_TREND_FILTER", False))
BIAS_MODE               = str(_S.get("BIAS_MODE", "relaxed"))

USE_VIX_DXY          = bool(_S.get("USE_VIX_DXY", False))
VIX_SOFT_MAX         = float(_S.get("VIX_SOFT_MAX", 22.0))
VIX_HARD_MAX         = float(_S.get("VIX_HARD_MAX", 28.0))
DXY_PC5_WARN         = float(_S.get("DXY_PC5_WARN", 0.8))
DXY_PC5_HARD         = float(_S.get("DXY_PC5_HARD", 1.6))
MACRO_SCORE_CAP      = float(_S.get("MACRO_SCORE_CAP", 0.15))
MACRO_CACHE_HOURS    = int(_S.get("MACRO_CACHE_HOURS", 12))
VIX_SYMBOL           = str(_S.get("VIX_SYMBOL", "^VIX"))
DXY_SYMBOL           = str(_S.get("DXY_SYMBOL", "DX=F"))

# ---- Exporta cualquier otra clave del JSON como atributo del módulo ----
# (no pisa las que ya definimos arriba)
for k, v in _S.items():
    if k not in globals():
        globals()[k] = v

# ---- Fail-fast mínimo (solo warning si falta Telegram)
_missing = []
if not TELEGRAM_TOKEN: _missing.append("TELEGRAM_TOKEN (.env)")
if not TELEGRAM_CHAT_ID: _missing.append("TELEGRAM_CHAT_ID (.env)")
if _missing:
    import logging
    logging.warning(
        "Faltan variables: %s (continuo; el envío a Telegram quedará desactivado)",
        ", ".join(_missing),
    )

def as_dict() -> Dict[str, Any]:
    """Devuelve el diccionario final de settings para depuración."""
    out = {k: v for k, v in globals().items()
           if k.isupper() and k not in {"__builtins__",}}
    return out
