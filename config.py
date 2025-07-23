# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv(".env")     # o la ruta donde ubiques el archivo

# Variables de entorno para autenticación y notificaciones
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")       # Clave API de Binance
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET") # Secreto API de Binance
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")         # Token del bot de Telegram
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")     # ID del chat para notificaciones

# === Parámetros del sistema ===
VOLUMEN_MINIMO_USDT = 300_000      # Monto mínimo en dólares para considerar un símbolo
GRIDS_GAP_PCT = 0.024              # Separación entre niveles de grids
MIN_SCORE_ALERTA = 30             # Puntuación mínima para enviar alerta a Telegram
MIN_SCORE_MERCADO = 65            # Umbral mínimo de score del mercado
LIMITE_ANALISIS = None             # Límite de símbolos a evaluar; None = sin límite

# === Exclusión de pares apalancados, experimentales o inestables ===
EXCLUDED_TERMS = (
    "UP", "DOWN", "BULL", "BEAR", "VENUS", "TUSD", "USDC",
    "LEVERAGED", "1000", "FDUSD", "BTCDOM", "TEST"  # Incluye tokens de test o dominancia
)

# === Rango de ATR permitido para filtrar criptos muy volátiles o planas ===
ATR_MIN = 0.5                      # ATR mínimo para descartar criptos con baja volatilidad
ATR_MAX = 5                        # ATR máximo para descartar criptos demasiado volátiles

# === RSI Rango para acumulación saludable ===
RSI_BUY_MIN = 40               # Nivel mínimo de RSI para considerar acumulación
RSI_BUY_MAX = 55               # Nivel máximo de RSI para considerar acumulación
RSI_OVERSOLD = 30              # Umbral de sobreventa
RSI_OVERBOUGHT = 70            # Umbral de sobrecompra
RSI_WEEKLY_OVERBOUGHT = 60     # RSI semanal por encima del cual se considera sobrecompra

# === Control de riesgo ===
MAX_CONSEC_LOSSES = 3                  # Máximo de pérdidas consecutivas permitidas
BTC_DROP_THRESHOLD = 0.03              # Caída intradía de BTC para pausar trading (3%)
VOLUME_DROP_THRESHOLD = 0.3            # Caída relativa del volumen global para pausar
TRADE_HISTORY_FILE = "data/trade_history.csv"  # Ruta del historial de operaciones
