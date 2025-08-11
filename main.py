# main.py
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional

import config
from utils.logger import setup_logging, get_audit_logger
from notifier.telegram import formatear_senal, enviar_telegram
from logic.analyzer import analizar_simbolo

# ⬇️ Ajusta estos imports a tus funciones reales
from utils.data_loader import get_klines  # get_klines(symbol, interval, limit) -> list[list]
from data.symbols import get_usdt_futures_universe  # universo de símbolos USDT perps

# ─────────────────────────────────────────────────────────

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)
audit = get_audit_logger()

LAST_TOP_PATH = os.path.join("output", "logs", ".last_top.json")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _load_last_top() -> dict:
    try:
        with open(LAST_TOP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_last_top(data: dict) -> None:
    _ensure_dir(os.path.dirname(LAST_TOP_PATH))
    with open(LAST_TOP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _hash_signal(symbol: str, tipo: str, entry: float, sl: float, tp: float) -> str:
    raw = f"{symbol}|{tipo}|{entry:.8f}|{sl:.8f}|{tp:.8f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ema_bias(klines: list) -> bool:
    """Sesgo simple: alcista si EMA20>EMA50 en 1d/1w. Devuelve True=alcista."""
    import pandas as pd
    import ta
    if not klines:
        return False
    df = pd.DataFrame(klines)[[4]].astype(float)  # close
    close = df[4]
    ema20 = ta.trend.EMAIndicator(close, 20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, 50).ema_indicator().iloc[-1]
    return bool(ema20 > ema50)


def _get_market_bias() -> Tuple[bool, bool]:
    """BTC/ETH alcistas (True/False) usando EMA20>EMA50 en diario."""
    try:
        btc_d = get_klines("BTCUSDT", "1d", limit=200)
        eth_d = get_klines("ETHUSDT", "1d", limit=200)
        return _ema_bias(btc_d), _ema_bias(eth_d)
    except Exception:
        return False, False


def run_once() -> None:
    audit.info("Inicio de escaneo…")
    btc_up, eth_up = _get_market_bias()

    # 1) Universo de símbolos (USDT perps)
    try:
        symbols: List[str] = get_usdt_futures_universe()
    except Exception as e:
        audit.error(f"No se pudo obtener el universo USDT Futures: {e}")
        return

    exclude = set(getattr(config, "EXCLUDE_SYMBOLS", []))
    symbols = [s for s in symbols if s not in exclude]

    resultados = []

    # 2) Descargar klines y analizar símbolo a símbolo (1d/1w)
    for sym in symbols:
        try:
            kl_d = get_klines(sym, "1d", limit=getattr(config, "LOOKBACK", 400))
            kl_w = get_klines(sym, "1w", limit=200)
            out = analizar_simbolo(sym, kl_d, kl_w, btc_up, eth_up)
            if out is None:
                continue
            tec, score, factors, _ = out
            resultados.append((tec, score))
        except Exception as e:
            audit.info(f"{sym} descartado por excepción: {e}")

    if not resultados:
        audit.info("Sin candidatos después del análisis.")
        return

    # 3) Ordenar por score y seleccionar top N
    resultados.sort(key=lambda x: x[1], reverse=True)
    top_n = getattr(config, "SEND_TOP_N", 10)
    candidatos = resultados[:top_n]

    # 4) Anti-spam: no enviar si el top no cambió y estamos en cooldown
    last_top = _load_last_top()
    last_hash = last_top.get("hash")
    last_ts = last_top.get("ts")
    cooldown_min = getattr(config, "COOLDOWN_MINUTES", 15)

    # Construir hash del top actual
    top_firma = "|".join(
        _hash_signal(
            tec.symbol,
            getattr(tec, "bias", tec.tipo),
            float(getattr(tec, "entry", tec.precio)),
            float(getattr(tec, "stop_loss", tec.sl)),
            float(getattr(tec, "take_profit", tec.tp)),
        )
        for tec, _ in candidatos
    )
    top_hash = hashlib.sha256(top_firma.encode("utf-8")).hexdigest()

    now = datetime.now(timezone.utc)
    if last_hash == top_hash and last_ts:
        try:
            last_dt = datetime.fromisoformat(last_ts)
            if now - last_dt < timedelta(minutes=cooldown_min):
                audit.info("Top sin cambios dentro del cooldown. No se envía Telegram.")
                return
        except Exception:
            pass

    # 5) Enviar a Telegram
    enviados = 0
    for tec, score in candidatos:
        msg = formatear_senal({
            "symbol": tec.symbol,
            "bias": getattr(tec, "bias", tec.tipo),
            "entry": float(getattr(tec, "entry", tec.precio)),
            "stop_loss": float(getattr(tec, "stop_loss", tec.sl)),
            "stop_profit": float(getattr(tec, "take_profit", tec.tp)),
            "score": score,
            "rsi_1d": getattr(tec, "rsi_1d", None),
            "macd_1d": getattr(tec, "macd_1d", None),
            "macd_signal_1d": getattr(tec, "macd_signal_1d", None),
            "volumen_actual": getattr(tec, "volumen_actual", None),
            "volumen_promedio": getattr(tec, "volumen_promedio", None),
            "Grids": getattr(tec, "grids", None),
        })
        enviar_telegram(msg)
        enviados += 1

    audit.info(f"Enviados {enviados} candidatos a Telegram.")

    # 6) Guardar estado de top para evitar spam
    _save_last_top({"hash": top_hash, "ts": now.isoformat()})


def run_bot() -> None:
    """Ejecución única. Si quieres convertirlo en servicio, llama run_once en intervalos."""
    try:
        run_once()
    except Exception as e:
        audit.error(f"Fallo en ejecución: {e}")


if __name__ == "__main__":
    run_bot()
