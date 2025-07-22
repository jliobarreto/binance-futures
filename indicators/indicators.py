"""Colección de indicadores técnicos de uso común."""
from __future__ import annotations

import pandas as pd
import ta


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    return ta.momentum.RSIIndicator(close, window=period).rsi()


def ema(close: pd.Series, period: int) -> pd.Series:
    return ta.trend.EMAIndicator(close, window=period).ema_indicator()


def macd(close: pd.Series):
    macd_obj = ta.trend.MACD(close)
    return macd_obj.macd(), macd_obj.macd_signal()


def bollinger_bands(close: pd.Series, period: int = 20):
    bb = ta.volatility.BollingerBands(close, window=period, window_dev=2)
    return bb.bollinger_hband(), bb.bollinger_lband()
