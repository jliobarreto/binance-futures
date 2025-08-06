"""Modelos de datos para el proyecto."""

from dataclasses import dataclass
from typing import Optional

__all__ = ["IndicadoresTecnicos"]

@dataclass
class IndicadoresTecnicos:
    symbol: str
    precio: float
    rsi_1d: float
    rsi_1w: float
    macd_1d: float
    macd_signal_1d: float
    ema20: float
    ema50: float
    ema200: float
    volumen_actual: float
    volumen_promedio: float
    atr: float
    tipo: str
    tp: float
    sl: float
    resistencia: float
    grids: int
    mfi: float
    obv: float
    adx: float
    boll_upper: float
    boll_lower: float
    trend_score: Optional[float] = None
    volume_score: Optional[float] = None
    momentum_score: Optional[float] = None
    volatility_score: Optional[float] = None
    rr_score: Optional[float] = None
    score: Optional[float] = None
    