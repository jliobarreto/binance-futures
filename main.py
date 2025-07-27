import asyncio
import os
from utils.logger import setup_logging

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)

from logic.contriver import run_bot


if __name__ == "__main__":
    asyncio.run(run_bot())
