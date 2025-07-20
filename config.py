# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv("api.env")     # o la ruta donde ubiques el archivo

# Variables de entorno para autenticación y notificaciones
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")       # Clave API de Binance
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET") # Secreto API de Binance
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")         # Token del bot de Telegram
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")     # ID del chat para notificaciones

# === Parámetros del sistema ===
VOLUMEN_MINIMO_USDT = 300_000      # Monto mínimo en dólares para considerar un símbolo
GRIDS_GAP_PCT = 0.024              # Separación entre niveles de grids
MIN_SCORE_ALERTA = 80              # Puntuación mínima para enviar alerta a Telegram
LIMITE_ANALISIS = None             # Límite de símbolos a evaluar; None = sin límite

# === Exclusión de pares apalancados, experimentales o inestables ===
EXCLUDED_TERMS = (
    "UP", "DOWN", "BULL", "BEAR", "VENUS", "TUSD", "USDC",
    "LEVERAGED", "1000", "FDUSD", "BTCDOM", "TEST", "USD"  # Incluye tokens de test o dominancia
)

# === Rango de ATR permitido para filtrar criptos muy volátiles o planas ===
ATR_MIN = 0.5                      # ATR mínimo para descartar criptos con baja volatilidad
ATR_MAX = 5                        # ATR máximo para descartar criptos demasiado volátiles

# === RSI Rango para acumulación saludable ===
RSI_BUY_MIN = 40                   # Nivel mínimo de RSI para considerar acumulación

