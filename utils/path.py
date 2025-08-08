from pathlib import Path

# Base directory for generated output anchored to the project root
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"

# Directory where log and CSV files are stored
LOGS_DIR = OUTPUT_DIR / "logs"

# Configuration file path
CONFIG_FILE = Path("config/settings.json")
