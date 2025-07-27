from __future__ import annotations

"""Utility functions to compute common technical indicators."""

import pandas as pd
import ta


def rsi(series: pd.Series, window: int = 14) -> float:
    """Return the latest RSI value for ``series``.

    Parameters
    ----------
    series:
        Price series to analyse.
    window:
        RSI look-back period.
    """
    if len(series) < window:
        return 0.0
    return ta.momentum.RSIIndicator(series, window=window).rsi().iloc[-1]


def macd(series: pd.Series) -> tuple[float, float]:
    """Return the latest MACD and signal line values."""
    if series.empty:
        return 0.0, 0.0
    macd_ind = ta.trend.MACD(series)
    return macd_ind.macd().iloc[-1], macd_ind.macd_signal().iloc[-1]


def ema(series: pd.Series, window: int) -> float:
    """Return the latest exponential moving average."""
    if len(series) < window:
        return float(series.iloc[-1]) if not series.empty else 0.0
    return ta.trend.EMAIndicator(series, window=window).ema_indicator().iloc[-1]


def average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> float:
    """Return the latest Average True Range value."""
    if len(high) < window or len(low) < window or len(close) < window:
        return 0.0
    atr = ta.volatility.AverageTrueRange(high, low, close, window=window)
    return atr.average_true_range().iloc[-1]


def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int = 14) -> float:
    """Return the latest Money Flow Index value."""
    if len(high) < window or len(low) < window or len(close) < window or len(volume) < window:
        return 0.0
    mfi = ta.volume.MFIIndicator(high, low, close, volume, window=window)
    return mfi.money_flow_index().iloc[-1]


def on_balance_volume(close: pd.Series, volume: pd.Series) -> float:
    """Return the latest On Balance Volume value."""
    if close.empty or volume.empty:
        return 0.0
    obv = ta.volume.OnBalanceVolumeIndicator(close, volume)
    return obv.on_balance_volume().iloc[-1]


def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> float:
    """Return the latest Average Directional Index value."""
    if len(high) < window or len(low) < window or len(close) < window:
        return 0.0
    indicator = ta.trend.ADXIndicator(high, low, close, window=window)
    return indicator.adx().iloc[-1]


def bollinger_bands(series: pd.Series, window: int = 20) -> tuple[float, float]:
    """Return the latest upper and lower Bollinger Bands."""
    if len(series) < window:
        last = float(series.iloc[-1]) if not series.empty else 0.0
        return last, last
    bb = ta.volatility.BollingerBands(series, window=window)
    return bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1]


__all__ = [
    "rsi",
    "macd",
    "ema",
    "average_true_range",
    "money_flow_index",
    "on_balance_volume",
    "adx",
    "bollinger_bands",
]
