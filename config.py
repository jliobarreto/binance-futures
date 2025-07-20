# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar variables desde un archivo .env en caso de existir
load_dotenv()

# === API Keys ===
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === Parámetros del sistema ===
VOLUMEN_MINIMO_USDT = 300_000      # Monto mínimo en dólares para considerar un símbolo
GRIDS_GAP_PCT = 0.024              # Separación entre niveles de grids
MIN_SCORE_ALERTA = 80              # Puntuación mínima para enviar alerta a Telegram
LIMITE_ANALISIS = 50               # Número máximo de símbolos a evaluar en cada ejecución

# === Exclusión de pares apalancados, experimentales o inestables ===
EXCLUDED_TERMS = (
    "UP", "DOWN", "BULL", "BEAR", "VENUS", "TUSD", "USDC",
    "LEVERAGED", "1000", "FDUSD", "BTCDOM", "TEST", "USD"  # Incluye tokens de test o dominancia
)

# === Rango de ATR permitido para filtrar criptos muy volátiles o planas ===
ATR_MIN = 0.5
ATR_MAX = 5

# === RSI Rango para acumulación saludable ===
RSI_BUY_MIN = 40
