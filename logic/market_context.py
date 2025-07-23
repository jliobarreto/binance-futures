# -*- coding: utf-8 -*-
"""Market context evaluation utilities."""

from dataclasses import dataclass
import logging
import pandas as pd
import ta
import yfinance as yf

@dataclass
class ContextoMercado:
    btc_alcista: bool
    eth_alcista: bool
    dxy_alcista: bool
    vix_valor: float
    mercado_favorable: bool
    score_total: float

def _descargar_cierre(ticker: str, interval: str, period: str = "400d") -> pd.Series:
    df = yf.download(
        ticker,
        interval=interval,
        period=period,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return pd.Series(dtype=float)
    return df["Close"].astype(float).squeeze("columns")


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
        btc_d = _descargar_cierre("BTC-USD", "1d")
    except Exception as e:
        logging.error(f"Error descargando BTC-USD 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        btc_w = _descargar_cierre("BTC-USD", "1wk")
    except Exception as e:
        logging.error(f"Error descargando BTC-USD 1wk: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        eth_d = _descargar_cierre("ETH-USD", "1d")
    except Exception as e:
        logging.error(f"Error descargando ETH-USD 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        eth_w = _descargar_cierre("ETH-USD", "1wk")
    except Exception as e:
        logging.error(f"Error descargando ETH-USD 1wk: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        dxy_d = _descargar_cierre("^DXY", "1d")
    except Exception as e:
        logging.error(f"Error descargando ^DXY 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    try:
        vix_d = _descargar_cierre("^VIX", "1d", "100d")
    except Exception as e:
        logging.error(f"Error descargando ^VIX 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False, 0.0)

    btc_alcista = _tendencia_alcista(btc_d) and _tendencia_alcista(btc_w)
    eth_alcista = _tendencia_alcista(eth_d) and _tendencia_alcista(eth_w)
    dxy_alcista = _tendencia_alcista(dxy_d)
    vix_valor = float(vix_d.iloc[-1]) if not vix_d.empty else 0.0

    mercado_favorable = btc_alcista and eth_alcista and not dxy_alcista and vix_valor < 25

    score_total = calcular_score_contexto(btc_alcista, eth_alcista, dxy_alcista, vix_valor)

    logging.info(
        f"BTC: {'Tendencia alcista confirmada' if btc_alcista else 'Tendencia bajista o indefinida'}"
    )
    logging.info(
        f"ETH: {'Tendencia alcista confirmada' if eth_alcista else 'Tendencia bajista o indefinida'}"
    )
    logging.info(
        f"DXY: {'En rango alcista' if dxy_alcista else 'En rango bajista o neutral'}"
    )
    logging.info(f"VIX: {vix_valor:.2f}")
    logging.info(f"Score total de contexto: {score_total}/100")
    if not mercado_favorable:
        logging.info("Mercado desfavorable -> análisis detenido")

    return ContextoMercado(
        btc_alcista=btc_alcista,
        eth_alcista=eth_alcista,
        dxy_alcista=dxy_alcista,
        vix_valor=vix_valor,
        mercado_favorable=mercado_favorable,
        score_total=score_total,
    )
