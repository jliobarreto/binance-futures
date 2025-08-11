# logic/levels.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Optional
import math
import pandas as pd

Bias = Literal["LONG", "SHORT"]

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Usa columna 'ATR' si existe; si no, calcula ATR (EMA-TR)."""
    if "ATR" in df.columns:
        return df["ATR"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

def _round_to_tick(price: float, tick_size: Optional[float]) -> float:
    if not tick_size or tick_size <= 0:
        return float(price)
    steps = round(price / tick_size)
    return float(steps * tick_size)

@dataclass
class Levels:
    entry: float
    stop_loss: float
    stop_profit: float
    risk_points: float      # R = |entry - stop_loss|
    rr: float               # TP/SL (si usamos TP = k·R, entonces rr = k)
    atr: float
    atr_pct: float          # ATR / close

def compute_levels(
    df: pd.DataFrame,
    bias: Bias,
    atr_sl_mult: float = 1.8,
    tp_r_mult: float = 2.0,
    swing_lookback: int = 14,
    tick_size: Optional[float] = None,
    atr_period: int = 14,
    max_atr_pct: Optional[float] = None,  # ej. 0.12 para 12%
) -> Levels:
    """
    Reglas:
      - Entry = close de la última vela CERRADA (usa el último registro del df).
      - SL LONG = min(swing_low, close - atr_sl_mult * ATR)
        SL SHORT = max(swing_high, close + atr_sl_mult * ATR)
      - R = |Entry - SL|
      - StopProfit = Entry ± tp_r_mult * R
      - Redondeo: si tick_size, redondea Entry/SL/TP al tick.

    df requiere columnas: open, high, low, close (floats). Si no trae ATR, se calcula.
    """
    required = {"open", "high", "low", "close"}
    if df.empty or not required.issubset(df.columns):
        raise ValueError("DataFrame debe tener columnas open, high, low, close")

    # Última vela del df (asumimos cerrada si vienes de klines REST)
    last = df.iloc[-1]
    close = float(last["close"])

    # ATR
    atr_series = _atr(df, period=atr_period)
    atr = float(atr_series.iloc[-1])
    if not (atr > 0 and math.isfinite(atr)):
        raise ValueError("ATR inválido (serie corta o datos faltantes)")

    highs = df["high"].astype(float)
    lows  = df["low"].astype(float)

    if bias == "LONG":
        swing = float(lows.tail(swing_lookback).min())
        sl_raw = min(swing, close - atr_sl_mult * atr)
        entry_raw = close
        r_raw = entry_raw - sl_raw
        tp_raw = entry_raw + tp_r_mult * r_raw
    else:  # SHORT
        swing = float(highs.tail(swing_lookback).max())
        sl_raw = max(swing, close + atr_sl_mult * atr)
        entry_raw = close
        r_raw = sl_raw - entry_raw
        tp_raw = entry_raw - tp_r_mult * r_raw

    # Fallback si R <= 0 (datos raros)
    if r_raw <= 0:
        if bias == "LONG":
            sl_raw = close - atr_sl_mult * atr
            r_raw = entry_raw - sl_raw
            tp_raw = entry_raw + tp_r_mult * r_raw
        else:
            sl_raw = close + atr_sl_mult * atr
            r_raw = sl_raw - entry_raw
            tp_raw = entry_raw - tp_r_mult * r_raw

    if r_raw <= 0:
        raise ValueError("R <= 0 tras fallback; revisar datos/parametrización.")

    # Sanidad por ATR%
    atr_pct = atr / max(close, 1e-12)
    if max_atr_pct is not None and atr_pct > max_atr_pct:
        raise ValueError(f"ATR% {atr_pct:.4f} > límite {max_atr_pct:.4f}")

    # Redondeo a tick
    entry = _round_to_tick(entry_raw, tick_size)
    stop_loss = _round_to_tick(sl_raw, tick_size)
    stop_profit = _round_to_tick(tp_raw, tick_size)

    # Recalcular R tras redondeo (lo reportamos para transparencia)
    risk_points = abs(entry - stop_loss)
    if risk_points <= 0:
        raise ValueError("R tras redondeo <= 0; ajustar tick_size/params.")

    return Levels(
        entry=entry,
        stop_loss=stop_loss,
        stop_profit=stop_profit,
        risk_points=risk_points,
        rr=float(tp_r_mult),   # TP/SL = k·R → rr = k
        atr=atr,
        atr_pct=atr_pct,
    )
