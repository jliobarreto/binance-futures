# -*- coding: utf-8 -*-
"""Market context evaluation utilities."""

from dataclasses import dataclass
import logging
import pandas as pd
import ta
import yfinance as yf
from config import SCORE_THRESHOLD_LONG, SCORE_THRESHOLD_SHORT

@dataclass
class ContextoMercado:
    btc_alcista: bool
    eth_alcista: bool
    dxy_alcista: bool
    vix_valor: float
    mercado_favorable: bool
    score_total: float
    score_long: float = 0.0
    score_short: float = 0.0
    apto_long: bool = False
    apto_short: bool = False

def _descargar_datos(ticker: str, interval: str, period: str = "400d") -> pd.DataFrame:
    df = yf.download(
        ticker,
        interval=interval,
        period=period,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return pd.DataFrame()
    return df


def _tendencia_alcista(close: pd.Series) -> bool:
    if close.empty or len(close) < 200:
        return False
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1]
    return ema50 > ema200 and close.iloc[-1] > ema50


def calcular_score_contexto(
    btc_alcista: bool, eth_alcista: bool, dxy_alcista: bool, vix_valor: float
) -> float:
    """Asigna un puntaje de 0 a 100 al contexto macro."""
    score = 0.0
    score += 40 if btc_alcista else 0
    score += 30 if eth_alcista else 0
    score += 20 if not dxy_alcista else 0
    if vix_valor < 20:
        score += 10
    elif vix_valor < 25:
        score += 5
    return score


def obtener_contexto_mercado() -> ContextoMercado:
    """Obtiene el contexto general del mercado usando datos macro."""
    try:
        btc_d = _descargar_datos("BTC-USD", "1d")
    except Exception as e:
        logging.error(f"Error descargando BTC-USD 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        btc_w = _descargar_datos("BTC-USD", "1wk")
    except Exception as e:
        logging.error(f"Error descargando BTC-USD 1wk: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        eth_d = _descargar_datos("ETH-USD", "1d")
    except Exception as e:
        logging.error(f"Error descargando ETH-USD 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        eth_w = _descargar_datos("ETH-USD", "1wk")
    except Exception as e:
        logging.error(f"Error descargando ETH-USD 1wk: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        dxy_d = _descargar_datos("^DXY", "1d")
    except Exception as e:
        logging.error(f"Error descargando ^DXY 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        vix_d = _descargar_datos("^VIX", "1d", "100d")
    except Exception as e:
        logging.error(f"Error descargando ^VIX 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    btc_close_d = btc_d["Close"] if "Close" in btc_d else pd.Series(dtype=float)
    btc_close_w = btc_w["Close"] if "Close" in btc_w else pd.Series(dtype=float)
    eth_close_d = eth_d["Close"] if "Close" in eth_d else pd.Series(dtype=float)
    eth_close_w = eth_w["Close"] if "Close" in eth_w else pd.Series(dtype=float)
    dxy_close_d = dxy_d["Close"] if "Close" in dxy_d else pd.Series(dtype=float)
    vix_close = vix_d["Close"] if "Close" in vix_d else pd.Series(dtype=float)

    btc_alcista = _tendencia_alcista(btc_close_d) and _tendencia_alcista(btc_close_w)
    eth_alcista = _tendencia_alcista(eth_close_d) and _tendencia_alcista(eth_close_w)
    dxy_alcista = _tendencia_alcista(dxy_close_d)
    vix_valor = float(vix_close.iloc[-1]) if not vix_close.empty else 0.0

    mercado_favorable = btc_alcista and eth_alcista and not dxy_alcista and vix_valor < 25

    score_total = calcular_score_contexto(btc_alcista, eth_alcista, dxy_alcista, vix_valor)

    # === Puntuación para operaciones LONG ===
    score_long = 0.0
    log_long: list[str] = []
    if not btc_w.empty:
        ema20 = ta.trend.EMAIndicator(btc_close_w, 20).ema_indicator().iloc[-1]
        ema50 = ta.trend.EMAIndicator(btc_close_w, 50).ema_indicator().iloc[-1]
        hl = len(btc_w) >= 2 and btc_w["Low"].iloc[-1] > btc_w["Low"].iloc[-2]
        if hl and ema20 > ema50:
            score_long += 25
            log_long.append("BTC semanal: Higher Low validado – EMA20 > EMA50")
        else:
            log_long.append("BTC semanal: sin Higher Low o cruce alcista")

        rsi_w = ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1] if len(btc_close_w) >= 14 else 0.0
        vol_up = len(btc_w) >= 2 and btc_w["Volume"].iloc[-1] > btc_w["Volume"].iloc[-2]
        if rsi_w > 50 and vol_up:
            score_long += 25
        log_long.append(f"RSI semanal: {rsi_w:.1f}")
    if not eth_d.empty and _tendencia_alcista(eth_close_d):
        score_long += 25
        log_long.append("ETH diario: tendencia alcista confirmada")
    else:
        log_long.append("ETH diario: sin tendencia alcista clara")
    dxy_bajista = not _tendencia_alcista(dxy_close_d)
    if dxy_bajista and vix_valor < 20:
        score_long += 25
        log_long.append("DXY bajista, VIX < 20")
    else:
        log_long.append("DXY o VIX sin confirmación")

    # === Puntuación para operaciones SHORT ===
    score_short = 0.0
    log_short: list[str] = []
    if not btc_w.empty:
        ema20 = ta.trend.EMAIndicator(btc_close_w, 20).ema_indicator().iloc[-1]
        ema50 = ta.trend.EMAIndicator(btc_close_w, 50).ema_indicator().iloc[-1]
        lh = len(btc_w) >= 2 and btc_w["High"].iloc[-1] < btc_w["High"].iloc[-2]
        if lh and ema20 < ema50:
            score_short += 25
            log_short.append("BTC semanal: Lower High validado – EMA20 < EMA50")
        else:
            log_short.append("BTC semanal: estructura neutral")

        rsi_w = ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1] if len(btc_close_w) >= 14 else 0.0
        vol_sell = len(btc_w) >= 2 and btc_w["Volume"].iloc[-1] >= btc_w["Volume"].iloc[-2]
        if rsi_w < 50 and vol_sell:
            score_short += 25
        log_short.append(f"RSI semanal: {rsi_w:.1f}")
    if not eth_d.empty and not _tendencia_alcista(eth_close_d):
        score_short += 25
        log_short.append("ETH diario: tendencia bajista confirmada")
    else:
        log_short.append("ETH diario: sin confirmación bajista")
    dxy_alza = _tendencia_alcista(dxy_close_d)
    if dxy_alza and vix_valor > 20:
        score_short += 25
        log_short.append("DXY alcista, VIX > 20")
    else:
        log_short.append("DXY lateral – sin presión clara")

    apto_long = score_long >= SCORE_THRESHOLD_LONG
    apto_short = score_short >= SCORE_THRESHOLD_SHORT

    logging.info("[LONG CONTEXT]")
    for linea in log_long:
        logging.info("  " + linea)
    logging.info(
        f"  Score global LONG: {score_long:.0f}/100 {'→ Apto para operar en largo' if apto_long else '→ No apto para operar en largo'}"
    )

    logging.info("[SHORT CONTEXT]")
    for linea in log_short:
        logging.info("  " + linea)
    logging.info(
        f"  Score global SHORT: {score_short:.0f}/100 {'→ Apto para operar en corto' if apto_short else '→ No apto para operar en corto'}"
    )

    if not (apto_long or apto_short):
        logging.info("Mercado desfavorable -> análisis detenido")

    return ContextoMercado(
        btc_alcista=btc_alcista,
        eth_alcista=eth_alcista,
        dxy_alcista=dxy_alcista,
        vix_valor=vix_valor,
        mercado_favorable=mercado_favorable,
        score_total=score_total,
        score_long=score_long,
        score_short=score_short,
        apto_long=apto_long,
        apto_short=apto_short,
    )
