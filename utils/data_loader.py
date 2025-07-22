"""Funciones de carga de datos para el sistema."""
from __future__ import annotations

from typing import Optional
import pandas as pd
from binance.client import Client
from config import BINANCE_API_KEY, BINANCE_API_SECRET


def descargar_klines(symbol: str, interval: str, limit: int = 500, client: Optional[Client] = None) -> pd.DataFrame:
    """Descarga velas de Binance y retorna un DataFrame."""
    if client is None:
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines).astype(float)
    return df


def cargar_csv(path: str) -> pd.DataFrame:
    """Carga un archivo CSV usando pandas."""
    return pd.read_csv(path)
utils/file_manager.py
