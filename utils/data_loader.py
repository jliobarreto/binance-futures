"""Funciones de carga de datos para el sistema."""
from __future__ import annotations

from typing import Optional, List
import time
import math
import logging
import requests
import pandas as pd

# Endpoints públicos (no requieren API key)
_SPOT_KLINES_URL = "https://api.binance.com/api/v3/klines"
_FUTS_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"

# Mapa de intervalo -> milisegundos
_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
    "1d": 86_400_000, "3d": 259_200_000,
    "1w": 604_800_000, "1M": 2_592_000_000,
}


def _interval_to_ms(interval: str) -> int:
    try:
        return _INTERVAL_MS[interval]
    except KeyError:
        raise ValueError(f"Intervalo no soportado: {interval}")


def _http_get(url: str, params: dict, retries: int = 3, timeout: int = 15) -> list:
    err = None
    for i in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            err = e
            # backoff exponencial simple
            time.sleep(0.5 * (2 ** i))
    raise RuntimeError(f"Fallo al obtener datos de {url}: {err}")


def _drop_unclosed(raw: list, interval: str) -> list:
    """Elimina la última vela si está en formación (según tiempo)."""
    if not raw:
        return raw
    interval_ms = _interval_to_ms(interval)
    now_ms = int(time.time() * 1000)
    # Estructura kline: [openTime, open, high, low, close, volume, closeTime, ...]
    open_time_last = int(raw[-1][0])
    if open_time_last + interval_ms > now_ms:
        raw = raw[:-1]
    return raw


def get_klines(
    symbol: str,
    interval: str,
    limit: int = 500,
    use_futures: bool = True,
    closed_only: bool = True,
) -> List[list]:
    """
    Devuelve klines formato Binance (lista de listas). Por defecto usa FUTURES.
    - closed_only: elimina la vela en formación.
    """
    url = _FUTS_KLINES_URL if use_futures else _SPOT_KLINES_URL
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    raw = _http_get(url, params)
    if closed_only:
        raw = _drop_unclosed(raw, interval)
    return raw


def descargar_klines(
    symbol: str,
    interval: str,
    limit: int = 500,
    use_futures: bool = True,
    closed_only: bool = True,
) -> pd.DataFrame:
    """
    Descarga klines y devuelve un DataFrame con columnas nombradas:
    ['open_time','open','high','low','close','volume','close_time', ...]
    """
    raw = get_klines(symbol, interval, limit=limit, use_futures=use_futures, closed_only=closed_only)
    if not raw:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume", "close_time"])

    df = pd.DataFrame(raw)
    # Tipos numéricos
    for col in [1, 2, 3, 4, 5]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Renombrar columnas principales
    rename = {
        0: "open_time", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume", 6: "close_time"
    }
    df.rename(columns=rename, inplace=True)
    return df


def cargar_csv(path: str) -> pd.DataFrame:
    """Carga un archivo CSV usando pandas."""
    return pd.read_csv(path)
