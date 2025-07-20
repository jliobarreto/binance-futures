# config.py
from datetime import timedelta

# === API Keys ===
BINANCE_API_KEY = "fcAy20fyHuii0of2n4jepQwLl3qskBtjaqX7YMCTuhqXD7cJCRP4XOOeqtARFv7I"
BINANCE_API_SECRET = "46yzE9EH0VGuerjdULmuFwCRh3te8b5c3rUCpEyqfMm9SAn2C2vGScJa5R1zZy3b"

TELEGRAM_TOKEN = "8132734898:AAHOxQyS_ouulRTsn9iU9c4q0jOe4CTgTGM"
TELEGRAM_CHAT_ID = "@hyperboni"

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
RSI_BUY_MAX = 55
RSI_OVERBOUGHT = 70
RSI_EXTREME_OVERBOUGHT = 80

# === Archivos y rutas ===
RUTA_EXCEL = "output/"
NOMBRE_EXCEL = "señales_long_short"
EXTENSION_EXCEL = ".xlsx"

# === Timezone o latencia (para futuras mejoras de sincronización) ===
TIMEZONE_OFFSET = timedelta(hours=-5)  # UTC-5 para Ecuador o similar

# === Modo verbose/logging ===
DEBUG = True  # Si True, imprime más detalles en consola para depuración

# === Parámetros de visualización para módulo de monitoreo (futuro) ===
MONITOR_REFRESH_INTERVAL = 30  # segundos entre actualización de pantalla
