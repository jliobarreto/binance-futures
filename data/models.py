"""Modelos de datos para el proyecto."""

from dataclasses import dataclass
from typing import Optional

__all__ = ["IndicadoresTecnicos"]


@dataclass
class IndicadoresTecnicos:
    # Básicos
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

    # Compatibilidad histórica
    tipo: str                  # LONG/SHORT antiguo (alias de bias)
    tp: float                  # antiguo take profit
    sl: float                  # antiguo stop loss
    resistencia: float
    grids: int

    # Indicadores extra
    mfi: float
    obv: float
    adx: float
    boll_upper: float
    boll_lower: float

    # NUEVOS (para señales listas a ejecutar)
    bias: Optional[str] = None               # LONG/SHORT moderno
    entry: Optional[float] = None            # precio de entrada
    stop_loss: Optional[float] = None        # alias moderno de sl
    take_profit: Optional[float] = None      # alias moderno de tp
    rr: Optional[float] = None               # TP/SL en múltiplos de R (ej. 2.0R)
    atr_pct: Optional[float] = None          # ATR / precio (volatilidad relativa)

    # Scores (opcionales)
    trend_score: Optional[float] = None
    volume_score: Optional[float] = None
    momentum_score: Optional[float] = None
    volatility_score: Optional[float] = None
    rr_score: Optional[float] = None
    score: Optional[float] = None

    def __post_init__(self):
        # Bias por compatibilidad
        if self.bias is None and self.tipo:
            self.bias = self.tipo

        # Entry por defecto = precio actual
        if self.entry is None:
            self.entry = self.precio

        # Sincronizar alias SL / TP modernos
        if self.stop_loss is None:
            self.stop_loss = self.sl
        if self.take_profit is None:
            self.take_profit = self.tp

        # ATR%
        if self.atr_pct is None:
            try:
                self.atr_pct = (self.atr / self.precio) if self.precio else None
            except Exception:
                self.atr_pct = None
