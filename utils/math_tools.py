# utils/math_tools.py

import numpy as np
import pandas as pd
from scipy.stats import linregress

def calcular_ratio_tp_sl(tp: float, sl: float) -> float:
    """Calcula el ratio entre Take Profit y Stop Loss."""
    if sl == 0:
        return np.nan
    return abs(tp - sl) / abs(sl)

def tendencia_lineal(data: list[float]) -> float:
    """Calcula la pendiente de una regresión lineal sobre una serie de precios."""
    if len(data) < 2:
        return 0
    x = np.arange(len(data))
    slope, _, _, _, _ = linregress(x, data)
    return slope

def detectar_divergencia(precios: list[float], indicador: list[float]) -> bool:
    """Detecta divergencias entre el precio y un indicador (RSI, MACD, etc)."""
    if len(precios) < 3 or len(indicador) < 3:
        return False

    precio_slope = tendencia_lineal(precios[-3:])
    indicador_slope = tendencia_lineal(indicador[-3:])

    return (precio_slope > 0 and indicador_slope < 0) or (precio_slope < 0 and indicador_slope > 0)

def media_movil_exponencial(data: list[float], period: int = 14) -> float:
    """Calcula la última EMA de una serie de datos."""
    return pd.Series(data).ewm(span=period, adjust=False).mean().iloc[-1]

def calcular_volatilidad(data: list[float]) -> float:
    """Calcula la volatilidad de una serie de precios como desviación estándar relativa."""
    if len(data) < 2:
        return 0
    return np.std(data) / np.mean(data)

def normalizar_valores(data: list[float]) -> list[float]:
    """Normaliza los valores de una lista entre 0 y 1."""
    arr = np.array(data)
    if arr.max() == arr.min():
        return [0.5] * len(arr)
    return ((arr - arr.min()) / (arr.max() - arr.min())).tolist()
