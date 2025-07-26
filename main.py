import asyncio
import os
from utils.logger import setup_logging

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)

from logic.orchestrator import run_bot
