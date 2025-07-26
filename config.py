# config.py
import os
import json
from dotenv import load_dotenv
from datetime import timedelta
from utils.path import CONFIG_FILE

load_dotenv(".env")     # o la ruta donde ubiques el archivo

# Variables de entorno para autenticación y notificaciones
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")       # Clave API de Binance
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET") # Secreto API de Binance
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")         # Token del bot de Telegram
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")     # ID del chat para notificaciones

# === Parámetros del sistema (se cargan desde settings.json) ===
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    _settings = json.load(f)

VOLUMEN_MINIMO_USDT = _settings.get("VOLUMEN_MINIMO_USDT", 300000)
GRIDS_GAP_PCT = _settings.get("GRIDS_GAP_PCT", 0.024)
MIN_SCORE_ALERTA = _settings.get("MIN_SCORE_ALERTA", 30)
SCORE_THRESHOLD_LONG = _settings.get("SCORE_THRESHOLD_LONG", 65)
SCORE_THRESHOLD_SHORT = _settings.get("SCORE_THRESHOLD_SHORT", 65)
LIMITE_ANALISIS = _settings.get("LIMITE_ANALISIS", None)
TOP_ANALISIS = _settings.get("TOP_ANALISIS", 30)

# === Exclusión de pares apalancados, experimentales o inestables ===
EXCLUDED_TERMS = (
    "UP",
    "DOWN",
    "BULL",
    "BEAR",
    "VENUS",
    "TUSD",
    "USDC",
    "LEVERAGED",
    "1000",
    "FDUSD",
    "BTCDOM",
    "TEST",  # Incluye tokens de test o dominancia
)

# === Rango de ATR permitido para filtrar criptos muy volátiles o planas ===
ATR_MIN = _settings.get("ATR_MIN", 0.5)
ATR_MAX = _settings.get("ATR_MAX", 5.0)

# === RSI Rango para acumulación saludable ===
RSI_BUY_MIN = _settings.get("RSI_BUY_MIN", 40)
RSI_BUY_MAX = _settings.get("RSI_BUY_MAX", 55)
RSI_OVERSOLD = _settings.get("RSI_OVERSOLD", 30)
RSI_OVERBOUGHT = _settings.get("RSI_OVERBOUGHT", 70)
RSI_WEEKLY_OVERBOUGHT = _settings.get("RSI_WEEKLY_OVERBOUGHT", 60)

# === Control de riesgo ===
MAX_CONSEC_LOSSES = _settings.get("MAX_CONSEC_LOSSES", 3)
BTC_DROP_THRESHOLD = _settings.get("BTC_DROP_THRESHOLD", 0.03)
VOLUME_DROP_THRESHOLD = _settings.get("VOLUME_DROP_THRESHOLD", 0.3)
TRADE_HISTORY_FILE = _settings.get("TRADE_HISTORY_FILE", "data/trade_history.csv")