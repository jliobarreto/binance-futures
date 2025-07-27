import sys
import types
from pathlib import Path

# Ensure repository root is importable before tests are collected
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import pytest

@pytest.fixture(autouse=True, scope="session")
def stub_config_module():
    cfg = types.ModuleType("config")
    cfg.TELEGRAM_TOKEN = ""
    cfg.TELEGRAM_CHAT_ID = ""
    cfg.SCORE_THRESHOLD_LONG = 65
    cfg.SCORE_THRESHOLD_SHORT = 65
    cfg.VOLUMEN_MINIMO_USDT = 300000
    cfg.GRIDS_GAP_PCT = 0.024
    cfg.MIN_SCORE_ALERTA = 30
    cfg.RSI_OVERBOUGHT = 70
    cfg.RSI_WEEKLY_OVERBOUGHT = 60
    cfg.BINANCE_API_KEY = ""
    cfg.BINANCE_API_SECRET = ""
    cfg.TOP_ANALISIS = 30
    sys.modules["config"] = cfg
    yield
    sys.modules.pop("config", None)
    if str(repo_root) in sys.path:
        sys.path.remove(str(repo_root))
