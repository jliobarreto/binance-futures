# tp_nxatr.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import logging
import math

# ──────────────────────────────────────────────────────────────────────────────
# Logging (formato similar a tus logs)
# ──────────────────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log_root = logging.getLogger("root")
log_audit = logging.getLogger("audit")

# ──────────────────────────────────────────────────────────────────────────────
# Tipos / Datos
# ──────────────────────────────────────────────────────────────────────────────
class Side(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Levels:
    entry: float     # Precio de entrada
    sl: float        # Stop Loss
    sp: float        # Take Profit (target crudo antes de saneo o ya saneado)
    atr: float       # ATR (mismo timeframe que usas para niveles)
    atr_pct: float   # ATR% en [0..1] (si viene 7.2 usa 0.072; si viene 7.2% como 7.2, lo normalizamos)
    rr: float        # R múltiplos de riesgo usados para construir el TP crudo (p. ej. 2.4)
    tick_size: Optional[float] = None  # Paso de precio del símbolo, si lo tienes

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_atr_pct(atr_pct: float) -> float:
    """
    Normaliza ATR% a fracción [0..1]. Si te llega 7.2 (es decir 7.2%), devuelve 0.072.
    Si ya viene 0.072, lo deja tal cual.
    """
    return atr_pct / 100.0 if atr_pct > 1.0 else atr_pct

def round_to_tick(price: float, tick_size: Optional[float]) -> float:
    if not tick_size or tick_size <= 0:
        return price
    # Evita drift por flotantes
    steps = round(price / tick_size)
    return round(steps * tick_size, 12)

def build_tp_from_rr(entry: float, sl: float, rr: float, side: Side) -> float:
    """
    Reconstruye el TP crudo usando RR, por si lo prefieres construir así.
    """
    risk = abs(entry - sl)
    if side == Side.LONG:
        return entry + rr * risk
    else:  # SHORT
        return entry - rr * risk

# ──────────────────────────────────────────────────────────────────────────────
# Núcleo: N×ATR adaptativo
# ──────────────────────────────────────────────────────────────────────────────
def choose_n_by_atr_pct(
    atr_pct: float,
    bands: Tuple[float, float] = (0.04, 0.08),  # 4% y 8%
    n_vals: Tuple[int, int, int] = (12, 8, 5)   # N para baja, media, alta volatilidad
) -> int:
    """
    Devuelve N en función de ATR%. Por defecto:
      - ATR% ≤ 4%  -> N=12
      - 4%<ATR%≤8% -> N=8
      - ATR% > 8%  -> N=5
    """
    ap = _normalize_atr_pct(atr_pct)
    low, mid = bands
    n_low, n_mid, n_high = n_vals
    if ap <= low:
        return n_low
    elif ap <= mid:
        return n_mid
    else:
        return n_high

def enforce_tp_nxatr(
    levels: Levels,
    side: Side,
    n: Optional[int] = None,
    bands: Tuple[float, float] = (0.04, 0.08),
    n_vals: Tuple[int, int, int] = (12, 8, 5),
    log_symbol: Optional[str] = None
) -> Levels:
    """
    Aplica el saneo de TP por N×ATR.
    - LONG:  TP_cap = entry + N*ATR; si TP > cap -> TP = cap
    - SHORT: TP_floor = entry - N*ATR; si TP < floor -> TP = floor
    - N es adaptativo por ATR% salvo que lo pases fijo.

    Devuelve una copia de Levels con el TP saneado (sp).
    Lanza logs estilo "[LEVELS_FIX] tp_cap_long" o "tp_floor_short".
    """
    entry, sl, tp_raw, atr = levels.entry, levels.sl, levels.sp, levels.atr
    tick = levels.tick_size
    ap = _normalize_atr_pct(levels.atr_pct)
    chosen_n = n if n is not None else choose_n_by_atr_pct(ap, bands=bands, n_vals=n_vals)

    sym = log_symbol or "SYMBOL"
    changed = False
    tp_new = tp_raw

    if side == Side.LONG:
        tp_cap = entry + chosen_n * atr
        if tp_raw > tp_cap:
            tp_new = tp_cap
            changed = True
            log_audit.info("[LEVELS_FIX] tp_cap_long (N=%s × ATR=%.6f) → cap=%.6f", chosen_n, atr, tp_cap)
    else:  # SHORT
        tp_floor = entry - chosen_n * atr
        # Evitar negativos por seguridad numérica
        tp_floor = max(tp_floor, 0.0)
        if tp_raw < tp_floor:
            tp_new = tp_floor
            changed = True
            log_audit.info("[LEVELS_FIX] tp_floor_short (N=%s × ATR=%.6f) → floor=%.6f", chosen_n, atr, tp_floor)

    # Redondeo a tick si lo tienes
    tp_new = round_to_tick(tp_new, tick)

    if changed:
        log_audit.info(
            "Fix TP %s → %s: entry=%.10g | SL=%.10g | TP_raw=%.10g | TP_fix=%.10g | ATR%%=%.4f | N=%d",
            side.value, (log_symbol or ""), entry, sl, tp_raw, tp_new, ap, chosen_n
        )
    return Levels(
        entry=entry,
        sl=sl,
        sp=tp_new,
        atr=atr,
        atr_pct=levels.atr_pct,
        rr=levels.rr,
        tick_size=tick
    )

# ──────────────────────────────────────────────────────────────────────────────
# Ejemplo de uso/integración
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Supongamos que calculas niveles con RR≈2.4R y ya tienes ATR & ATR%
    # LONG (p. ej., SOLUSDT del log: RR≈2.4)
    lv_long = Levels(
        entry=175.55,
        sl=155.72,
        sp=build_tp_from_rr(175.55, 155.72, rr=2.4, side=Side.LONG),  # TP crudo por RR
        atr=9.55,                # ejemplo (ajusta al tuyo)
        atr_pct=0.0544,          # 5.44% ya en fracción (si llega 5.44 -> lo normalizamos)
        rr=2.4,
        tick_size=0.01
    )
    lv_long_fix = enforce_tp_nxatr(lv_long, side=Side.LONG, log_symbol="SOLUSDT")

    # SHORT (p. ej., STGUSDT del log)
    lv_short = Levels(
        entry=0.1906,
        sl=0.21246,
        sp=build_tp_from_rr(0.1906, 0.21246, rr=2.4, side=Side.SHORT),
        atr=0.0109,              # ejemplo (ajusta al tuyo)
        atr_pct=0.0573,          # 5.73%
        rr=2.4,
        tick_size=0.0001
    )
    lv_short_fix = enforce_tp_nxatr(lv_short, side=Side.SHORT, log_symbol="STGUSDT")

    log_root.info(
        "Niveles SOLUSDT: Entry=%.2f | SL=%.2f | TP_raw=%.2f | TP_fix=%.2f",
        lv_long.entry, lv_long.sl, lv_long.sp, lv_long_fix.sp
    )
    log_root.info(
        "Niveles STGUSDT: Entry=%.4f | SL=%.5f | TP_raw=%.5f | TP_fix=%.5f",
        lv_short.entry, lv_short.sl, lv_short.sp, lv_short_fix.sp
    )
