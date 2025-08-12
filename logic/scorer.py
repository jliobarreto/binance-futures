# logic/scorer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import math

# Importa config si existe; usa defaults si no.
try:
    import config  # type: ignore
except Exception:
    class _Cfg:
        MIN_SCORE_ALERTA = 55.0
        ADX_MIN = 12.0
        RR_MIN = 1.8
        ATR_PCT_MIN = 0.005
        ATR_PCT_MAX = 0.30
        BIAS_MODE = "relaxed"  # relaxed | strict | position
    config = _Cfg()  # type: ignore


# ───────────────────────── helpers ─────────────────────────
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _lin(x: float, x0: float, x1: float) -> float:
    """Interpolación lineal 0..1 entre x0..x1."""
    if x1 == x0:
        return 0.0
    return _clamp((x - x0) / (x1 - x0), 0.0, 1.0)

def _score_band(x: Optional[float], lo: float, lo_ideal: float, hi_ideal: float, hi: float) -> float:
    """
    0 si x<=lo o x>=hi; 1 si x en [lo_ideal, hi_ideal]; rampas lineales en los bordes.
    """
    if x is None or math.isnan(x):
        return 0.0
    if x <= lo or x >= hi:
        return 0.0
    if lo_ideal <= x <= hi_ideal:
        return 1.0
    if x < lo_ideal:
        return _lin(x, lo, lo_ideal)
    return 1.0 - _lin(x, hi_ideal, hi)


# ───────────────────────── inferir sesgo ─────────────────────────
def inferir_bias(ctx: Dict) -> str:
    """
    Devuelve 'LONG' | 'SHORT' | 'NONE' a partir de EMAs diarias y semanales + RSI.
    Espera claves: ema_fast_h1, ema_slow_h1, ema_fast_h4, ema_slow_h4, rsi14_h1, rsi14_h4, atr_pct (opcional).
    Modo 'position': requiere alineación SEMANAL clara y que el diario no contradiga.
    """
    e20d = ctx.get("ema_fast_h1")
    e50d = ctx.get("ema_slow_h1")
    e20w = ctx.get("ema_fast_h4")
    e50w = ctx.get("ema_slow_h4")
    rsi_d = ctx.get("rsi14_h1")
    rsi_w = ctx.get("rsi14_h4")
    atrp  = ctx.get("atr_pct")

    mode = str(getattr(config, "BIAS_MODE", "relaxed")).lower()

    # ATR% kill opcional (protege de activos hipervolátiles)
    atr_max = getattr(config, "ATR_PCT_MAX", None)
    if atr_max is not None and isinstance(atr_max, (int, float)) and atrp is not None:
        if atrp > float(atr_max) * 1.05:  # tolerancia
            return "NONE"

    up_d   = (e20d is not None and e50d is not None and e20d > e50d)
    up_w   = (e20w is not None and e50w is not None and e20w > e50w)
    down_d = (e20d is not None and e50d is not None and e20d < e50d)
    down_w = (e20w is not None and e50w is not None and e20w < e50w)

    # ── Modo posición (sesgo de meses): manda la SEMANAL ──
    if mode in ("position", "weekly_strict"):
        # LONG: semanal alcista y RSI_w >= 50; diario no debe contradecir (vale lateral o alcista).
        if up_w and (rsi_w is None or rsi_w >= 50) and (not down_d) and (rsi_d is None or rsi_d >= 45):
            return "LONG"
        # SHORT: semanal bajista y RSI_w <= 50; diario no debe contradecir (vale lateral o bajista).
        if down_w and (rsi_w is None or rsi_w <= 50) and (not up_d) and (rsi_d is None or rsi_d <= 55):
            return "SHORT"
        return "NONE"

    # ── Modo estricto: exige coherencia D+W ──
    if mode == "strict":
        if up_d and up_w and (rsi_d is None or rsi_d >= 45) and (rsi_w is None or rsi_w >= 45):
            return "LONG"
        if down_d and down_w and (rsi_d is None or rsi_d <= 55) and (rsi_w is None or rsi_w <= 55):
            return "SHORT"
        return "NONE"

    # ── Modo relajado (por defecto): permite semanal neutral si el diario no contradice ──
    if up_d and not down_w:
        return "LONG"
    if down_d and not up_w:
        return "SHORT"
    return "NONE"


# ───────────────────────── modelo esperado ─────────────────────────
@dataclass
class _TecView:
    precio: float
    rsi_1d: Optional[float]
    rsi_1w: Optional[float]
    ema20: Optional[float]
    ema50: Optional[float]
    ema200: Optional[float]
    volumen_actual: Optional[float]
    volumen_promedio: Optional[float]
    atr: Optional[float]
    tipo: str  # bias
    tp: Optional[float]
    sl: Optional[float]


# ───────────────────────── score ─────────────────────────
def calcular_score(tec, bias: Optional[str] = None) -> Tuple[float, Dict[str, float]]:
    """
    Devuelve (score_total, factores) donde factores = {trend, volume, momentum, volatility, risk_reward}.
    0..100. Ponderaciones:
      - Trend      30
      - Momentum   20
      - Volatility 15
      - Volume     10
      - R/R        25
    """
    tv = _TecView(
        precio=float(getattr(tec, "precio", getattr(tec, "close", 0.0)) or 0.0),
        rsi_1d=_asfloat(getattr(tec, "rsi_1d", None)),
        rsi_1w=_asfloat(getattr(tec, "rsi_1w", None)),
        ema20=_asfloat(getattr(tec, "ema20", None)),
        ema50=_asfloat(getattr(tec, "ema50", None)),
        ema200=_asfloat(getattr(tec, "ema200", None)),
        volumen_actual=_asfloat(getattr(tec, "volumen_actual", None)),
        volumen_promedio=_asfloat(getattr(tec, "volumen_promedio", None)),
        atr=_asfloat(getattr(tec, "atr", None)),
        tipo=str(bias or getattr(tec, "tipo", "") or "").upper(),
        tp=_asfloat(getattr(tec, "tp", getattr(tec, "take_profit", None))),
        sl=_asfloat(getattr(tec, "sl", getattr(tec, "stop_loss", None))),
    )

    # Ponderaciones
    W_TREND, W_MOM, W_VOLAT, W_VOL, W_RR = 30.0, 20.0, 15.0, 10.0, 25.0

    # 1) Trend
    trend_s = 0.0
    if tv.tipo == "LONG":
        if _gt(tv.ema20, tv.ema50) and _gt(tv.ema50, tv.ema200):
            trend_s = 1.0
        elif _gt(tv.ema20, tv.ema50):
            trend_s = 0.6
        elif tv.ema200 is not None and tv.precio > tv.ema200:
            trend_s = 0.3
    elif tv.tipo == "SHORT":
        if _lt(tv.ema20, tv.ema50) and _lt(tv.ema50, tv.ema200):
            trend_s = 1.0
        elif _lt(tv.ema20, tv.ema50):
            trend_s = 0.6
        elif tv.ema200 is not None and tv.precio < tv.ema200:
            trend_s = 0.3

    # 2) Momentum (RSI)
    if tv.tipo == "LONG":
        mom_d = _score_band(tv.rsi_1d, 35, 45, 60, 75)
        mom_w = _score_band(tv.rsi_1w, 35, 45, 60, 75)
    elif tv.tipo == "SHORT":
        mom_d = _score_band(tv.rsi_1d, 25, 40, 55, 65)
        mom_w = _score_band(tv.rsi_1w, 25, 40, 55, 65)
    else:
        mom_d = mom_w = 0.0
    momentum_s = 0.6 * mom_d + 0.4 * mom_w

    # 3) Volatility (ATR%)
    atr_pct = None
    if tv.atr is not None and tv.precio > 0:
        atr_pct = tv.atr / tv.precio
    atr_min = float(getattr(config, "ATR_PCT_MIN", 0.005))  # 0.5%
    atr_max = float(getattr(config, "ATR_PCT_MAX", 0.30))   # 30%
    if atr_pct is None:
        volat_s = 0.0
    else:
        mid = 0.5 * (atr_min + atr_max)
        lo_i, hi_i = 0.8 * mid, 1.2 * mid
        volat_s = _score_band(atr_pct, atr_min, lo_i, hi_i, atr_max)

    # 4) Volume (vitalidad = vol_act / vol_avg)
    vitalidad = None
    if tv.volumen_actual and tv.volumen_promedio and tv.volumen_promedio > 0:
        vitalidad = tv.volumen_actual / tv.volumen_promedio
    if vitalidad is None:
        vol_s = 0.0
    else:
        if vitalidad >= 1.2:
            vol_s = 1.0
        elif vitalidad >= 1.0:
            vol_s = 0.7 + 0.3 * _lin(vitalidad, 1.0, 1.2)
        else:
            vol_s = 0.7 * _lin(vitalidad, 0.5, 1.0)

    # 5) Risk/Reward
    entry = _asfloat(getattr(tec, "entry", None)) or tv.precio
    rr_s = 0.0
    if tv.tp is not None and tv.sl is not None and entry is not None:
        r = abs(entry - tv.sl)
        R = (abs(tv.tp - entry) / r) if r > 0 else 0.0
        if R >= 2.5:
            rr_s = 1.0
        elif R >= 2.0:
            rr_s = 0.9
        elif R >= 1.5:
            rr_s = 0.6
        elif R >= 1.2:
            rr_s = 0.3
        else:
            rr_s = 0.0
    else:
        rr_s = 0.0

    factors = {
        "trend": round(W_TREND * trend_s, 4),
        "momentum": round(W_MOM * momentum_s, 4),
        "volatility": round(W_VOLAT * volat_s, 4),
        "volume": round(W_VOL * vol_s, 4),
        "risk_reward": round(W_RR * rr_s, 4),
    }
    total = round(sum(factors.values()), 6)
    return total, factors


# ───────────────────────── util internos ─────────────────────────
def _asfloat(x) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None

def _gt(a: Optional[float], b: Optional[float]) -> bool:
    return (a is not None) and (b is not None) and (a > b)

def _lt(a: Optional[float], b: Optional[float]) -> bool:
    return (a is not None) and (b is not None) and (a < b)
