# utils/data_loader.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("data_loader")

# ─────────────────────────────────────────────────────────
# Endpoints Binance (Spot y USDT-M Futures)
# ─────────────────────────────────────────────────────────

SPOT_BASES = [
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

FAPI_BASES = [
    "https://fapi.binance.com",
    # Dominio alternativo histórico; se mantiene como fallback.
    "https://fapi.binancefuture.com",
]

SPOT_KLINES_PATH = "/api/v3/klines"
FAPI_KLINES_PATH = "/fapi/v1/klines"

# Límite máximo soportado por el endpoint (Binance FAPI soporta 1500; Spot 1000).
SPOT_LIMIT_MAX = 1000
FAPI_LIMIT_MAX = 1500

# Caché local (en disco) para responses GET
CACHE_DIR = os.path.join("output", ".cache", "http")
os.makedirs(CACHE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────
# Sesión HTTP con reintentos
# ─────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    session = requests.Session()
    # Retries idempotentes para GET: maneja 429 y 5xx con backoff
    retry = Retry(
        total=4,  # total de reintentos
        connect=3,
        read=3,
        status=4,
        backoff_factor=0.6,  # 0.6, 1.2, 2.4, 4.8s (aprox)
        status_forcelist=(429, 418, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    # Montamos genéricamente para https
    session.mount("https://", adapter)
    # UA simple para identificar el bot (opcional)
    session.headers.update(
        {
            "User-Agent": "scan-bot/1.0 (+https://example.local) requests",
            "Accept": "application/json",
        }
    )
    return session


SESSION = _build_session()

# ─────────────────────────────────────────────────────────
# Utilidades: caché en disco
# ─────────────────────────────────────────────────────────

def _cache_key(url: str, params: Dict[str, Any]) -> str:
    key_raw = f"{url}|{json.dumps(params, sort_keys=True, separators=(',', ':'))}"
    return hashlib.sha1(key_raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.json")


def _cache_read(key: str, ttl_secs: int) -> Optional[Any]:
    path = _cache_path(key)
    try:
        st = os.stat(path)
        age = time.time() - st.st_mtime
        if age > ttl_secs:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _cache_write(key: str, payload: Any) -> None:
    path = _cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as e:
        logger.debug(f"No se pudo escribir caché {path}: {e}")


# ─────────────────────────────────────────────────────────
# HTTP GET robusto con fallback de base URLs
# ─────────────────────────────────────────────────────────

class HttpGetError(RuntimeError):
    pass


def _http_get_first_ok(
    bases: List[str],
    path: str,
    params: Dict[str, Any],
    timeout: Tuple[float, float] = (5.0, 20.0),  # (connect, read)
    cache_ttl: int = 0,
    sleep_between: float = 0.3,  # pequeña pausa entre fallbacks
) -> Any:
    """
    Intenta GET sobre cada base en orden hasta obtener 200 OK.
    Usa caché en disco si cache_ttl>0.
    """
    # Normaliza tipos simples para params
    norm_params = {}
    for k, v in params.items():
        if isinstance(v, bool):
            norm_params[k] = "true" if v else "false"
        else:
            norm_params[k] = v

    # Clave de caché estable (por URL + params)
    first_url = f"{bases[0]}{path}"
    key = _cache_key(first_url, norm_params)

    if cache_ttl > 0:
        cached = _cache_read(key, cache_ttl)
        if cached is not None:
            return cached

    last_err: Optional[Exception] = None
    for i, base in enumerate(bases):
        url = f"{base}{path}"
        try:
            resp = SESSION.get(url, params=norm_params, timeout=timeout)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    # algunos endpoints devuelven lista plana JSON; si falla json() se intenta texto
                    data = json.loads(resp.text)
                if cache_ttl > 0:
                    _cache_write(key, data)
                return data

            # 429/418: rate limit; respetar Retry-After si viene
            if resp.status_code in (429, 418):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_s = float(retry_after)
                        time.sleep(min(wait_s, 5.0))
                    except Exception:
                        time.sleep(1.0)
                else:
                    time.sleep(1.0)

            last_err = HttpGetError(f"HTTP {resp.status_code} on {url}: {resp.text[:200]}")
        except requests.Timeout as e:
            last_err = e
        except requests.RequestException as e:
            last_err = e
        except Exception as e:
            last_err = e

        # Pausa breve antes de probar el siguiente base
        time.sleep(sleep_between)

    raise HttpGetError(str(last_err) if last_err else "Fallo GET desconocido")


# ─────────────────────────────────────────────────────────
# API pública: klines
# ─────────────────────────────────────────────────────────

Interval = str  # ej. "1m","5m","1h","1d","1w","1M"


def _clamp_limit(limit: int, use_futures: bool) -> int:
    lmax = FAPI_LIMIT_MAX if use_futures else SPOT_LIMIT_MAX
    if limit <= 0:
        return 1
    if limit > lmax:
        return lmax
    return limit


def get_klines(
    symbol: str,
    interval: Interval,
    limit: int = 500,
    start_time: Optional[int] = None,  # epoch ms
    end_time: Optional[int] = None,    # epoch ms
    use_futures: bool = True,
    cache_ttl: int = 30,
    timeout: Tuple[float, float] = (5.0, 20.0),
) -> List[List[Union[str, float, int]]]:
    """
    Devuelve klines crudos (lista de listas) tal y como los entrega Binance.
    Compatible con analyzer._klines_to_df (usa columnas [1..5]).

    - symbol: "BTCUSDT", "ETHUSDT", etc.
    - interval: "1m","5m","1h","4h","1d","1w","1M"
    - limit: nº de velas (se clamp a 1000 Spot / 1500 Futures)
    - start_time/end_time: opcionales en epoch ms
    - use_futures: True para USDT-M Perpetual (FAPI), False para Spot
    - cache_ttl: (s) caché en disco. 0 para desactivar.
    - timeout: (connect, read)

    Retorna [] si no hay datos o ante error controlado.
    Lanza HttpGetError sólo si TODOS los endpoints fallan.
    """
    limit = _clamp_limit(int(limit), use_futures=use_futures)

    params: Dict[str, Any] = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    bases = FAPI_BASES if use_futures else SPOT_BASES
    path = FAPI_KLINES_PATH if use_futures else SPOT_KLINES_PATH

    try:
        data = _http_get_first_ok(
            bases=bases,
            path=path,
            params=params,
            timeout=timeout,
            cache_ttl=cache_ttl,
            sleep_between=0.25,
        )
        # Validación mínima: esperamos una lista de listas
        if isinstance(data, list) and (len(data) == 0 or isinstance(data[0], list)):
            return data
        # Algunos proxies devuelven dict con "code"/"msg"
        if isinstance(data, dict) and "code" in data:
            logger.warning(f"Binance error {data.get('code')}: {data.get('msg')}")
            return []
        # Fallback final: intenta parsear texto si vino como string JSON
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return []
    except HttpGetError as e:
        # No escalo la excepción para no detener el escaneo completo
        logger.info(f"get_klines fallback a [] por error: {e}")
        return []
    except Exception as e:
        logger.info(f"get_klines error inesperado: {e}")
        return []


# ─────────────────────────────────────────────────────────
# Conveniencia: DataFrame rápido (opcional, no usado por analyzer)
# ─────────────────────────────────────────────────────────

def get_klines_df(
    symbol: str,
    interval: Interval,
    limit: int = 500,
    **kwargs: Any,
):
    """
    Devuelve un DataFrame con columnas estándar:
    ["open_time","open","high","low","close","volume","close_time",
     "quote_volume","trades","taker_base","taker_quote","ignore"]

    Nota: analyzer.py NO usa esto; es sólo utilitario de depuración/analítica.
    """
    import pandas as pd

    rows = get_klines(symbol, interval, limit=limit, **kwargs)
    cols = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base",
        "taker_quote",
        "ignore",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)

    try:
        df = pd.DataFrame(rows, columns=cols)
        # Tipifica numéricas
        for c in ("open", "high", "low", "close", "volume", "quote_volume", "taker_base", "taker_quote"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception:
        # Si no hay 12 columnas por cambios del proveedor, no fallar
        return pd.DataFrame(rows)
