from pathlib import Path

# === RUTAS BASE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === CARPETAS CLAVE ===
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# === ARCHIVOS CLAVE ===
XLSX_PATH = OUTPUT_DIR / "registro_operaciones.xlsx"
SYMBOLS_FILE = DATA_DIR / "symbols.json"
CONFIG_FILE = CONFIG_DIR / "settings.yaml"

# Crear carpetas si no existen
for directory in [DATA_DIR, OUTPUT_DIR, LOGS_DIR, CONFIG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
