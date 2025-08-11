from __future__ import annotations
from typing import Tuple, Dict, Optional
import math

# ───────────────────────── helpers ─────────────────────────

def _get(obj, name: str, default=None):
    """Lee atributo o clave dict de forma segura."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _tri_score(x: Optional[float], lo: float, lo_ok: float, hi_ok: float, hi: float) -> float:
    """
    Triángulo: 0 en [−∞,lo], sube lineal hasta 1 en lo_ok,
    se mantiene en 1 hasta hi_ok y baja lineal a 0 en hi y [hi,+∞].
    Devuelve 0..1
    """
    if x is None or not math.isfinite(x):
        return 0.0
    if x <= lo or x >= hi:
        return 0.0
    if x < lo_ok:
        return (x - lo) / max(lo_ok - lo, 1e-12)
    if x > hi_ok:
        return (hi - x) / max(hi - hi_ok, 1e-12)
    return 1.0

# ───────────────────────── bias ─────────────────────────

def inferir_bias(tec) -> str:
    """
    LONG si EMA_fast>EMA_slow en H1 y H4; SHORT si <.
    Fallback con RSI promedio >=50 (LONG) o <=50 (SHORT).
    """
    ef1 = _get(tec, "ema_fast_h1")
    es1 = _get(tec, "ema_slow_h1")
    ef4 = _get(tec, "ema_fast_h4")
    es4 = _get(tec, "ema_slow_h4")

    if None not in (ef1, es1, ef4, es4):
        if ef1 > es1 and ef4 > es4:
            return "LONG"
        if ef1 < es1 and ef4 < es4:
            return "SHORT"

    r1 = _get(tec, "rsi14_h1")
    r4 = _get(tec, "rsi14_h4")
    if r1 is not None and r4 is not None:
        r = (float(r1) + float(r4)) / 2.0
        if r >= 50:
            return "LONG"
        if r <= 50:
            return "SHORT"
    return "NONE"

# ───────────────────────── score principal ─────────────────────────

def calcular_score(tec, bias: Optional[str] = None) -> tuple[float, dict[str, float]]:
    """
    Calcula un score 0..100 con 5 componentes (20 pts c/u):
      - trend, volume, momentum, volatility, risk_reward

    Parámetros esperados (si existen):
      ema_fast_h1/ema_slow_h1, ema_fast_h4/ema_slow_h4,
      rsi14_h1, rsi14_h4,
      vol_ma_ratio_h1 (o vol_ma_ratio), volume_usdt_24h,
      atr_pct_h1 (o atr_pct), close,
      entry, stop_loss, take_profit  (para puntuar RR).

    Retorna:
      (score_total, {"trend":..., "volume":..., "momentum":..., "volatility":..., "risk_reward":...})
    """
    # 1) Bias
    if not bias:
        bias = inferir_bias(tec)

    parts: Dict[str, float] = {
        "trend": 0.0, "volume": 0.0, "momentum": 0.0, "volatility": 0.0, "risk_reward": 0.0
    }

    # 2) Tendencia (0..20)
    ef1, es1 = _get(tec, "ema_fast_h1"), _get(tec, "ema_slow_h1")
    ef4, es4 = _get(tec, "ema_fast_h4"), _get(tec, "ema_slow_h4")
    if None not in (ef1, es1, ef4, es4) and bias in ("LONG", "SHORT"):
        ok1 = (ef1 > es1) if bias == "LONG" else (ef1 < es1)
        ok4 = (ef4 > es4) if bias == "LONG" else (ef4 < es4)
        parts["trend"] = (10.0 if ok1 else 0.0) + (10.0 if ok4 else 0.0)

    # 3) Volumen (0..20)
    vol_ratio = _get(tec, "vol_ma_ratio_h1", _get(tec, "vol_ma_ratio"))
    if vol_ratio is not None and math.isfinite(float(vol_ratio)):
        # 1.0 = media → 10 pts; 2.0x = 20 pts; <0.8 = 0
        x = float(vol_ratio)
        parts["volume"] = 20.0 * _clip01((x - 0.8) / (2.0 - 0.8))
    else:
        vol_usdt = _get(tec, "volume_usdt_24h")
        if vol_usdt is not None and float(vol_usdt) > 0:
            # 25M → 0 ; 75M → 10 ; 150M → 20 (escala log suave)
            v = max(float(vol_usdt), 1.0)
            score01 = _clip01((math.log10(v) - math.log10(25e6)) / (math.log10(150e6) - math.log10(25e6)))
            parts["volume"] = 20.0 * score01

    # 4) Momentum (0..20) según bias y RSI promedio
    r1, r4 = _get(tec, "rsi14_h1"), _get(tec, "rsi14_h4")
    if r1 is not None and r4 is not None and bias in ("LONG", "SHORT"):
        r = (float(r1) + float(r4)) / 2.0
        target = 55.0 if bias == "LONG" else 45.0
        # banda “saludable” ±10 → fuera cae a 0
        parts["momentum"] = 20.0 * _clip01(1.0 - abs(r - target) / 10.0)

    # 5) Volatilidad (0..20) con ATR%
    atrp = _get(tec, "atr_pct_h1", _get(tec, "atr_pct"))
    if atrp is None:
        # intenta calcular con atr/close si existen
        atr = _get(tec, "atr14_h1", _get(tec, "atr"))
        close = _get(tec, "close")
        if atr is not None and close not in (None, 0):
            atrp = float(atr) / float(close)
    if atrp is not None:
        # ideal: 1%–6%; 0.5% o 12% son 0
        parts["volatility"] = 20.0 * _tri_score(float(atrp), 0.005, 0.01, 0.06, 0.12)

    # 6) Risk/Reward (0..20) si ya tienes niveles
    entry = _get(tec, "entry")
    sl = _get(tec, "stop_loss")
    tp = _get(tec, "take_profit")
    if None not in (entry, sl, tp):
        entry, sl, tp = float(entry), float(sl), float(tp)
        r = abs(entry - sl)
        if r > 0:
            rr = abs(tp - entry) / r  # 1R..2R..3R
            parts["risk_reward"] = 20.0 * _clip01((rr - 1.0) / (2.0 - 1.0))  # 1R→0 ; 2R→20 (cap)

    total = sum(parts.values())
    return total, parts
