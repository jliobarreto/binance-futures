# main.py
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import config
from utils.logger import setup_logging, get_audit_logger
from notifier.telegram import formatear_senal, enviar_telegram
from logic.analyzer import analizar_simbolo

# Datos/mercado
from utils.data_loader import get_klines  # get_klines(symbol, interval, limit) -> list[list]
from data.symbols import get_usdt_futures_universe  # universo de símbolos USDT perps

# Macro (VIX/DXY) – opcional, con caché interna
from utils.macro import get_macro_state, macro_kill_reason, macro_multiplier

# ─────────────────────────────────────────────────────────

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)
audit = get_audit_logger()

LOG_DIR = os.path.join("output", "logs")
LAST_TOP_PATH = os.path.join(LOG_DIR, ".last_top.json")
SYMBOL_LOCK_PATH = os.path.join(LOG_DIR, ".symbol_last.json")
DAY_COUNT_PATH = os.path.join(LOG_DIR, ".day_count.json")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: str, data: dict) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _hash_signal(symbol: str, tipo: str, entry: float, sl: float, tp: float) -> str:
    raw = f"{symbol}|{tipo}|{entry:.8f}|{sl:.8f}|{tp:.8f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ema_bias(klines: list) -> bool:
    """Sesgo simple: alcista si EMA20>EMA50. Devuelve True=alcista."""
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

    # 0) Macro (VIX/DXY): se consulta una vez, con caché
    ms = get_macro_state()
    vix_txt = "—" if ms.vix_last is None else f"{ms.vix_last:.1f}"
    dxy_txt = "—" if ms.dxy_last is None else f"{ms.dxy_last:.2f}"
    vix_pc5_txt = "—" if ms.vix_pc5 is None else f"{ms.vix_pc5:+.2f}%"
    dxy_pc5_txt = "—" if ms.dxy_pc5 is None else f"{ms.dxy_pc5:+.2f}%"
    audit.info(f"Macro → VIX {vix_txt} ({vix_pc5_txt}/5d) | DXY {dxy_txt} ({dxy_pc5_txt}/5d)")

    # 1) Régimen de mercado (BTC/ETH)
    btc_up, eth_up = _get_market_bias()

    # 2) Universo USDT Perpetuos (Futures)
    try:
        symbols: List[str] = get_usdt_futures_universe()
    except Exception as e:
        audit.error(f"No se pudo obtener el universo USDT Futures: {e}")
        return

    exclude = set(getattr(config, "EXCLUDE_SYMBOLS", []))
    symbols = [s for s in symbols if s not in exclude]
    audit.info(f"Universo USDT Futures: {len(symbols)} símbolos")

    resultados: List[tuple] = []

    # 3) Descargar klines y analizar símbolo a símbolo (1d/1w)
    for sym in symbols:
        try:
            kl_d = get_klines(sym, "1d", limit=getattr(config, "LOOKBACK", 400))
            kl_w = get_klines(sym, "1w", limit=200)
            out = analizar_simbolo(sym, kl_d, kl_w, btc_up, eth_up)
            if out is None:
                continue
            tec, score, factors, _ = out

            # Bias del activo
            bias = (getattr(tec, "bias", None) or getattr(tec, "tipo", "")).upper()

            # 3.a) Kill-switch macro (solo en escenarios adversos; no estorba)
            reason = macro_kill_reason(bias, ms)
            if reason:
                audit.info(f"{sym} descartado por macro [{reason}]")
                continue

            # 3.b) Ajuste suave del score (cap ±15%)
            mult, notes = macro_multiplier(bias, ms)
            adj_score = round(float(score) * mult, 2)

            context = []
            if notes:
                context.append(" | ".join(notes))

            resultados.append((tec, adj_score, context))

        except Exception as e:
            audit.info(f"{sym} descartado por excepción: {e}")

    audit.info(f"Candidatos tras análisis: {len(resultados)}")
    if not resultados:
        audit.info("Sin candidatos después del análisis.")
        return

    # 4) Ordenar por score ajustado y seleccionar top N
    resultados.sort(key=lambda x: x[1], reverse=True)
    top_n = getattr(config, "SEND_TOP_N", 10)
    candidatos = resultados[:top_n]

    # 5) Anti-spam (hash del top) + cooldown global
    last_top = _load_json(LAST_TOP_PATH)
    last_hash = last_top.get("hash")
    last_ts = last_top.get("ts")
    cooldown_min = getattr(config, "COOLDOWN_MINUTES", 15)

    # Construir hash del top actual (basado en niveles, no en score)
    def _sig_tuple(tec_obj):
        return _hash_signal(
            tec_obj.symbol,
            (getattr(tec_obj, "bias", tec_obj.tipo) or "").upper(),
            float(getattr(tec_obj, "entry", tec_obj.precio)),
            float(getattr(tec_obj, "stop_loss", tec_obj.sl)),
            float(getattr(tec_obj, "take_profit", tec_obj.tp)),
        )

    top_firma = "|".join(_sig_tuple(tec) for tec, _, _ in candidatos)
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

    # 6) Cupo diario + cooldown por símbolo
    last_sent = _load_json(SYMBOL_LOCK_PATH)  # {symbol: ts_epoch}
    day_count = _load_json(DAY_COUNT_PATH)    # {YYYY-MM-DD: count}
    today_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sent_today = int(day_count.get(today_key, 0))
    cap = getattr(config, "DAILY_SEND_CAP", 15)
    cool_h = getattr(config, "SYMBOL_COOLDOWN_HOURS", 24)

    final: List[tuple] = []
    now_ts = time.time()

    for tec, adj_score, context in candidatos:
        if sent_today >= cap:
            break
        sym = tec.symbol
        last_ts_sym = float(last_sent.get(sym, 0))
        if now_ts - last_ts_sym < cool_h * 3600:
            continue
        final.append((tec, adj_score, context))
        last_sent[sym] = now_ts
        sent_today += 1

    if not final:
        audit.info("No hay candidatos que pasen cooldown por símbolo o cupo diario.")
        # Aun así guardamos el hash para evitar spam
        _save_json(LAST_TOP_PATH, {"hash": top_hash, "ts": now.isoformat()})
        return

    # 7) Enviar a Telegram
    enviados = 0
    for tec, adj_score, context in final:
        msg = formatear_senal({
            "symbol": tec.symbol,
            "bias": getattr(tec, "bias", tec.tipo),
            "entry": float(getattr(tec, "entry", tec.precio)),
            "stop_loss": float(getattr(tec, "stop_loss", tec.sl)),
            "stop_profit": float(getattr(tec, "take_profit", tec.tp)),
            "score": adj_score,
            "timeframe": "1d/1w",
            "context": context,
        })
        enviar_telegram(msg)
        enviados += 1

    audit.info(f"Enviados {enviados} candidatos a Telegram.")

    # 8) Guardar estados (hash top, locks y conteo diario)
    _save_json(LAST_TOP_PATH, {"hash": top_hash, "ts": now.isoformat()})
    _save_json(SYMBOL_LOCK_PATH, last_sent)
    day_count[today_key] = sent_today
    _save_json(DAY_COUNT_PATH, day_count)


def run_bot() -> None:
    """Ejecución única. Para servicio, llama run_once() en intervalos."""
    try:
        run_once()
    except Exception as e:
        audit.error(f"Fallo en ejecución: {e}")


if __name__ == "__main__":
    run_bot()
