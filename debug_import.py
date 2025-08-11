# scripts/scan_debug.py
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from typing import List, Tuple

import numpy as np

import config
from utils.logger import setup_logging, get_audit_logger
from utils.data_loader import get_klines  # get_klines(symbol, interval, limit)
from logic.analyzer import analizar_simbolo
from notifier.telegram import TelegramNotifier

# Universo de símbolos (USDT Perps)
try:
    # tu helper para futures USDT
    from data.symbols import get_usdt_futures_universe
except Exception:
    # fallback (por si tu repo expone otra función)
    from data.symbols import obtener_top_usdt as get_usdt_futures_universe  # type: ignore


audit = get_audit_logger()


def _get_market_bias() -> tuple[bool, bool]:
    """BTC/ETH alcistas (True/False) usando EMA20>EMA50 diario."""
    try:
        import pandas as pd
        import ta

        def _ema_bias(kl):
            if not kl:
                return False
            ser = pd.DataFrame(kl)[[4]].astype(float)[4]
            ema20 = ta.trend.EMAIndicator(ser, 20).ema_indicator().iloc[-1]
            ema50 = ta.trend.EMAIndicator(ser, 50).ema_indicator().iloc[-1]
            return bool(ema20 > ema50)

        btc_d = get_klines("BTCUSDT", "1d", limit=200)
        eth_d = get_klines("ETHUSDT", "1d", limit=200)
        return _ema_bias(btc_d), _ema_bias(eth_d)
    except Exception:
        return False, False


def _rr(entry: float, sl: float, tp: float) -> float:
    try:
        r = abs(entry - sl)
        return float(abs(tp - entry) / r) if r > 0 else 0.0
    except Exception:
        return 0.0


def _fmt(x: float) -> str:
    ax = abs(x)
    if ax >= 100:
        return f"{x:.2f}"
    if ax >= 1:
        return f"{x:.4f}"
    if ax >= 0.01:
        return f"{x:.5f}"
    return f"{x:.8f}"


def _build_signal_dict(tec, score: float) -> dict:
    entry = float(getattr(tec, "entry", getattr(tec, "precio", np.nan)))
    sl = float(getattr(tec, "stop_loss", getattr(tec, "sl", np.nan)))
    tp = float(getattr(tec, "take_profit", getattr(tec, "tp", np.nan)))
    bias = str(getattr(tec, "bias", getattr(tec, "tipo", "NONE"))).upper()

    rr = _rr(entry, sl, tp)
    atr = float(getattr(tec, "atr", np.nan))
    price = float(getattr(tec, "precio", entry))
    atr_pct = (atr / price) if (price and price > 0) else np.nan
    adx = float(getattr(tec, "adx", np.nan))

    # “context” para que el mensaje sea útil al trader
    ctx = []
    if not np.isnan(atr_pct):
        ctx.append(f"ATR%={atr_pct:.4f}")
    if not np.isnan(adx):
        ctx.append(f"ADX={adx:.2f}")
    if rr > 0:
        ctx.append(f"RR≈{rr:.2f}R")

    return {
        "symbol": tec.symbol,
        "bias": bias,
        "score": round(float(score), 4),
        "timeframe": "1d/1w",
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "context": ctx,
        # estos contadores se rellenan en el envío en tiempo real
        "evaluated": 0,
        "eligible": 0,
        "sent": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Escaneo + envío directo a Telegram (debug)."
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=getattr(config, "MIN_SCORE_ALERTA", 55),
        help="Umbral mínimo de score para enviar (default: config.MIN_SCORE_ALERTA).",
    )
    parser.add_argument(
        "--min-vol-usdt",
        type=float,
        default=getattr(config, "VOLUMEN_MINIMO_USDT", 2e7),
        help="Mínimo volumen USDT estimado en la vela diaria (default: config.VOLUMEN_MINIMO_USDT).",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=getattr(config, "LOOKBACK", 400),
        help="Velas diarias a descargar (default: config.LOOKBACK).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=getattr(config, "SEND_TOP_N", 10),
        help="Cuántas señales enviar a Telegram (default: config.SEND_TOP_N).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log a nivel DEBUG.",
    )
    args = parser.parse_args()

    # Logging
    mode = os.getenv("APP_MODE", "production")
    setup_logging(mode)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Verificación credenciales Telegram
    token = getattr(config, "TELEGRAM_TOKEN", None)
    chat_id = getattr(config, "TELEGRAM_CHAT_ID", None)
    if not token or not chat_id:
        print("❌ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en config.")
        return
    tbot = TelegramNotifier(token, str(chat_id))

    # Régimen de mercado base
    btc_up, eth_up = _get_market_bias()
    audit.info(f"Régimen → BTC alcista={btc_up} | ETH alcista={eth_up}")

    # Universo
    try:
        symbols: List[str] = get_usdt_futures_universe()
    except Exception as e:
        audit.error(f"No se pudo obtener el universo USDT Futures: {e}")
        return

    exclude = set(getattr(config, "EXCLUDE_SYMBOLS", []))
    symbols = [s for s in symbols if s not in exclude]
    print(f"Universo USDT Futures: {len(symbols)}")

    resultados: List[Tuple[object, float]] = []
    ok = 0
    fails = 0

    # Escaneo
    for idx, sym in enumerate(symbols, 1):
        if idx % 50 == 0:
            print(f"  …{idx} símbolos procesados")
        try:
            kl_d = get_klines(sym, "1d", limit=args.lookback)
            kl_w = get_klines(sym, "1w", limit=200)
            out = analizar_simbolo(sym, kl_d, kl_w, btc_up, eth_up)
            if out is None:
                fails += 1
                continue
            tec, score, _factors, _ = out

            # filtro mínimo de score (duro)
            if float(score) < float(args.min_score):
                fails += 1
                continue

            # filtro rápido de liquidez (USDT aprox. con vela actual)
            precio = float(getattr(tec, "precio", getattr(tec, "entry", 0.0)))
            vol_usdt_est = float(getattr(tec, "volumen_actual", 0.0)) * max(precio, 0.0)
            if vol_usdt_est < float(args.min_vol_usdt):
                fails += 1
                continue

            resultados.append((tec, float(score)))
            ok += 1

        except Exception as e:
            audit.info(f"{sym} descartado por EXC: {e}")
            fails += 1

    # Ordenar por score y truncar al top solicitado
    resultados.sort(key=lambda x: x[1], reverse=True)
    candidatos = resultados[: int(args.top)]

    print("\n===== RESUMEN =====")
    print(f"Total: {len(symbols)} | OK: {ok} | Fails: {fails}")
    if not candidatos:
        print("No hay candidatos para enviar.")
        return

    # Enviar a Telegram
    enviados = 0
    for i, (tec, score) in enumerate(candidatos, 1):
        sig = _build_signal_dict(tec, score)
        sig["evaluated"] = len(symbols)
        sig["eligible"] = ok
        sig["sent"] = i

        ok_send = tbot.send_signal(sig)
        if ok_send:
            enviados += 1
            audit.info(f"Telegram OK → {tec.symbol} (score {score:.2f})")
        else:
            audit.error(f"Telegram FAIL → {tec.symbol} (score {score:.2f})")

    print(f"\n✅ Enviados a Telegram: {enviados}/{len(candidatos)}")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Terminado: {ts}")


if __name__ == "__main__":
    main()
