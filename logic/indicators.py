# indicators.py
import pandas as pd
import numpy as np
import ta


def calcular_rsi(close: pd.Series, periodo: int = 14) -> float:
    return ta.momentum.RSIIndicator(close, window=periodo).rsi().iloc[-1]


def calcular_macd(close: pd.Series):
    macd_obj = ta.trend.MACD(close)
    return macd_obj.macd().iloc[-1], macd_obj.macd_signal().iloc[-1]


def calcular_ema(close: pd.Series, periodo: int) -> float:
    return ta.trend.EMAIndicator(close, window=periodo).ema_indicator().iloc[-1]


def calcular_atr(high: pd.Series, low: pd.Series, close: pd.Series, periodo: int = 14) -> float:
    return ta.volatility.AverageTrueRange(high, low, close, window=periodo).average_true_range().iloc[-1]


def calcular_adx(high: pd.Series, low: pd.Series, close: pd.Series, periodo: int = 14) -> float:
    return ta.trend.ADXIndicator(high, low, close, window=periodo).adx().iloc[-1]


def calcular_bollinger_bands(close: pd.Series, periodo: int = 20):
    bb = ta.volatility.BollingerBands(close, window=periodo, window_dev=2)
    return bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1], bb.bollinger_mavg().iloc[-1]


def calcular_mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, periodo: int = 14) -> float:
    return ta.volume.MFIIndicator(high, low, close, volume, window=periodo).money_flow_index().iloc[-1]