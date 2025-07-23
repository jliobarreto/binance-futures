# -*- coding: utf-8 -*-
"""Market context evaluation utilities.

Este módulo calcula el contexto de mercado en función de diversos
indicadores macro y evalúa de forma diferenciada las condiciones para
operar en **largo** o en **corto**.  Cada dirección obtiene un puntaje de
0 a 100 basado en varios factores técnicos y de sentimiento.
"""

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
    """Descarga precios históricos usando :mod:`yfinance`.

    Parameters
    ----------
    ticker: str
        Símbolo a descargar (por ejemplo ``"BTC-USD"``).
    interval: str
        Intervalo de las velas (``"1d"``, ``"1wk"``...).
    period: str, default ``"400d"``
        Rango de datos a obtener.
    """

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


def _descargar_seguro(ticker: str, interval: str, period: str = "400d") -> pd.DataFrame:
    """Descarga datos gestionando cualquier excepción.

    En caso de error, registra el problema y devuelve un :class:`DataFrame`
    vacío para mantener la ejecución del sistema sin interrupciones.
    """

    try:
        return _descargar_datos(ticker, interval, period)
    except Exception as exc:  # pragma: no cover - dependencias externas
        logging.error(f"Error descargando {ticker} {interval}: {exc}")
        return pd.DataFrame()


def _tendencia_alcista(close: pd.Series | pd.DataFrame) -> bool:
    """Valida si una serie está en tendencia alcista usando EMAs.

    Se asegura que ``close`` sea una :class:`pandas.Series` antes de
    calcular los indicadores técnicos para evitar errores de dimensiones.
    """

    if isinstance(close, pd.DataFrame):
        close = close.squeeze()

    assert isinstance(close, pd.Series), "close debe ser una Serie 1D"

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
    """Obtiene el contexto general del mercado.

    Descarga precios de BTC, ETH, DXY y VIX para calcular distintas
    señales de tendencia y volatilidad.  Con esta información se
    asignan dos puntajes (``score_long`` y ``score_short``) que indican la
    conveniencia de operar en cada dirección.
    """
    btc_d = _descargar_seguro("BTC-USD", "1d")
    btc_w = _descargar_seguro("BTC-USD", "1wk")
    eth_d = _descargar_seguro("ETH-USD", "1d")
    eth_w = _descargar_seguro("ETH-USD", "1wk")
    dxy_d = _descargar_seguro("^DXY", "1d")
    vix_d = _descargar_seguro("^VIX", "1d", "100d")

    if btc_d.empty or btc_w.empty or eth_d.empty or eth_w.empty or dxy_d.empty or vix_d.empty:
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
    score_long_btc = 0
    score_long_rsi = 0
    score_long_eth = 0
    score_long_dxy = 0
    log_long: list[str] = []
