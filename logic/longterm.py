"""Herramientas para validar la tendencia de largo plazo."""

from __future__ import annotations

import pandas as pd
import ta

from config import RSI_WEEKLY_OVERBOUGHT


def valida_entrada_largo_plazo(
    df_d: pd.DataFrame,
    df_w: pd.DataFrame,
    ema_short_window: int = 50,
    ema_long_window: int = 200,
    rsi_window: int = 14,
    rsi_overbought: int = RSI_WEEKLY_OVERBOUGHT,
) -> tuple[bool, str]:
    """Evalúa si un activo mantiene una tendencia alcista de largo plazo.

    Parameters
    ----------
    df_d : pandas.DataFrame
        Datos diarios del activo con columnas OHLCV.
    df_w : pandas.DataFrame
        Datos semanales del activo con columnas OHLCV.
    ema_short_window : int, default ``50``
        Ventana de la EMA rápida usada en el marco diario.
    ema_long_window : int, default ``200``
        Ventana de la EMA lenta usada en el marco diario.
    rsi_window : int, default ``14``
        Ventana para el cálculo del RSI semanal.
    rsi_overbought : int, default ``config.RSI_WEEKLY_OVERBOUGHT``
        Umbral máximo permitido para el RSI semanal.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` si el activo cumple los criterios, en caso
        contrario ``(False, motivo)`` indicando la causa del rechazo.
    """

    if len(df_d) < ema_long_window or len(df_w) < rsi_window:
        return False, "Datos insuficientes"

    close_d = df_d[4].astype(float)
    close_w = df_w[4].astype(float)

    ema_fast = ta.trend.EMAIndicator(close_d, ema_short_window).ema_indicator().iloc[-1]
    ema_slow = ta.trend.EMAIndicator(close_d, ema_long_window).ema_indicator().iloc[-1]
    price = close_d.iloc[-1]

    if not (ema_fast > ema_slow and price > ema_fast):
        return False, "Tendencia diaria bajista"

    rsi_weekly = ta.momentum.RSIIndicator(close_w, rsi_window).rsi().iloc[-1]
    if rsi_weekly > rsi_overbought:
        return False, "RSI semanal sobrecomprado"

    return True, ""
