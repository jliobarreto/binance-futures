# data/symbols.py
from __future__ import annotations

from typing import List, Optional
import time
import requests

# ───────────────────────── Config locales ─────────────────────────
_BINANCE_SPOT_EXCHANGEINFO = "https://api.binance.com/api/v3/exchangeInfo"
_BINANCE_FUT_EXCHANGEINFO  = "https://fapi.binance.com/fapi/v1/exchangeInfo"
_BINANCE_FUT_TICKER_24H    = "https://fapi.binance.com/fapi/v1/ticker/24hr"

# Caché simple en memoria
_CACHE: dict = {
    "fut_exchange_info": {"ts": 0.0, "data": None},
    "spot_exchange_info": {"ts": 0.0, "data": None},
}
CACHE_TTL_SEC = 15 * 60  # 15 min


def _get_json(url: str, timeout: int = 12) -> dict:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _get_futures_exchange_info() -> dict:
    now = time.time()
    item = _CACHE["fut_exchange_info"]
    if item["data"] is not None and (now - item["ts"] < CACHE_TTL_SEC):
        return item["data"]
    data = _get_json(_BINANCE_FUT_EXCHANGEINFO)
    _CACHE["fut_exchange_info"] = {"ts": now, "data": data}
    return data


def _get_spot_exchange_info() -> dict:
    now = time.time()
    item = _CACHE["spot_exchange_info"]
    if item["data"] is not None and (now - item["ts"] < CACHE_TTL_SEC):
        return item["data"]
    data = _get_json(_BINANCE_SPOT_EXCHANGEINFO)
    _CACHE["spot_exchange_info"] = {"ts": now, "data": data}
    return data


def get_usdt_futures_universe(limit: Optional[int] = None) -> List[str]:
    """
    Devuelve símbolos USDT PERPETUAL en estado TRADING (Futures).
    Ej.: ["BTCUSDT", "ETHUSDT", ...]
    """
    info = _get_futures_exchange_info()
    symbols = []
    for s in info.get("symbols", []):
        if (
            s.get("status") == "TRADING"
            and s.get("quoteAsset") == "USDT"
            and s.get("contractType") == "PERPETUAL"
        ):
            symbols.append(s.get("symbol"))
    symbols = sorted(set(filter(None, symbols)))
    if limit is not None:
        return symbols[:limit]
    return symbols


# ───────────────────────── Compatibilidad (Spot) ─────────────────────────
# Mantengo tu función original por si la usas en otra parte.
try:
    from binance.client import Client  # type: ignore
except Exception:
    Client = object  # fallback para hints


def obtener_top_usdt(client: Client, limit: int | None = None) -> list[str]:
    """
    (Spot) Top USDT por volumen. Se mantiene por compatibilidad.
    """
    tickers = []
    try:
        # Si hay cliente, úsalo; si no, caemos al endpoint público de futures/spot
        tickers = client.get_ticker_24hr()  # type: ignore[attr-defined]
    except Exception:
        # Fallback a ticker de futures (si se quiere; no es idéntico al de spot)
        try:
            tickers = _get_json(_BINANCE_FUT_TICKER_24H)
        except Exception:
            tickers = []

    usdt_tickers = [t for t in tickers if str(t.get("symbol", "")).endswith("USDT")]
    usdt_tickers.sort(
        key=lambda t: float(t.get("quoteVolume") or t.get("volume") or 0.0),
        reverse=True,
    )
    symbols = [t.get("symbol") for t in usdt_tickers if t.get("symbol")]
    if limit is not None:
        return symbols[:limit]
    return symbols


__all__ = ["get_usdt_futures_universe", "obtener_top_usdt"]
