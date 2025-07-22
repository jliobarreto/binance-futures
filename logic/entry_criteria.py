"""Criterios de entrada para operaciones de largo plazo."""

from __future__ import annotations

import pandas as pd
import ta

from logic import structure_validator, risk_manager
from utils.math_tools import detectar_divergencia


def valida_entrada_largo_plazo(df_d: pd.DataFrame, df_w: pd.DataFrame) -> bool:
    """Evalúa si existen condiciones sólidas para una entrada de largo plazo.

    Este método consolida varias comprobaciones técnicas:
    1. Detección de consolidación y ruptura.
    2. Confirmación de pullback con mayor volumen.
    3. Validación de la relación recompensa/riesgo usando el ATR.
    4. Búsqueda de divergencia positiva en el RSI.

    Retorna ``True`` solamente si todas las condiciones se cumplen.
    """

    # 1. Ruptura confirmada en diario y semanal
    if not structure_validator.ruptura_confirmada(df_d.iloc[:-1]):
        return False
    if not structure_validator.ruptura_confirmada(df_w):
        return False

    # 2. Pullback con volumen superior a la vela de ruptura
    vol_breakout = df_d[5].iloc[-2]
    vol_pullback = df_d[5].iloc[-1]
    cierre_breakout = df_d[4].iloc[-2]
    cierre_pullback = df_d[4].iloc[-1]
    if not (cierre_pullback < cierre_breakout and vol_pullback > vol_breakout):
        return False

    # 3. Niveles de SL/TP con ATR y validación de reward/risk
    atr = ta.volatility.AverageTrueRange(df_d[2], df_d[3], df_d[4], window=14)
    atr_val = atr.average_true_range().iloc[-1]
    precio = df_d[4].iloc[-1]
    sl, tp = risk_manager.niveles_atr(precio, atr_val, "LONG")
    riesgo = abs(precio - sl)
    recompensa = abs(tp - precio)
    if riesgo == 0 or recompensa / riesgo <= 2:
        return False

    # 4. Divergencia positiva con RSI
    rsi = ta.momentum.RSIIndicator(df_d[4], window=14).rsi()
    if not detectar_divergencia(df_d[4].tolist(), rsi.tolist()):
        return False

    return True
