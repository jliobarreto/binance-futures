# utils/macro.py
from __future__ import annotations
import os, json, time
from dataclasses import dataclass
from typing import Optional, Tuple, List

import yfinance as yf

@dataclass
class MacroState:
    vix_last: Optional[float]
    vix_pc5: Optional[float]
    dxy_last: Optional[float]
    dxy_pc5: Optional[float]
    ts: float

def _last_and_pc5(symbol: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        df = yf.Ticker(symbol).history(period="15d", interval="1d", auto_adjust=False)
        if df.empty or len(df.index) < 6:
            return None, None
        c = df["Close"]
        last = float(c.iloc[-1])
        pc5 = (c.iloc[-1] / c.iloc[-6] - 1.0) * 100.0
        return last, pc5
    except Exception:
        return None, None

def _cache_path() -> str:
    path = os.path.join("output", "cache")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "macro.json")

def get_macro_state() -> MacroState:
    # Config y cache
    try:
        import config
        vix_sym = getattr(config, "VIX_SYMBOL", "^VIX")
        dxy_sym = getattr(config, "DXY_SYMBOL", "DX=F")
        ttl_hours = float(getattr(config, "MACRO_CACHE_HOURS", 6))
    except Exception:
        vix_sym, dxy_sym, ttl_hours = "^VIX", "DX=F", 6.0

    cache_file = _cache_path()
    now = time.time()
    # lee cache
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            j = json.load(f)
        if now - float(j.get("ts", 0)) < ttl_hours * 3600:
            return MacroState(
                vix_last=j.get("vix_last"), vix_pc5=j.get("vix_pc5"),
                dxy_last=j.get("dxy_last"), dxy_pc5=j.get("dxy_pc5"),
                ts=float(j.get("ts", now))
            )
    except Exception:
        pass

    vix_last, vix_pc5 = _last_and_pc5(vix_sym)
    dxy_last, dxy_pc5 = _last_and_pc5(dxy_sym)
    state = MacroState(vix_last, vix_pc5, dxy_last, dxy_pc5, ts=now)

    # guarda cache (best-effort)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(state.__dict__, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return state

def macro_kill_reason(bias: str, ms: MacroState) -> Optional[str]:
    """Regla dura: solo corta en escenarios realmente adversos."""
    try:
        import config
        use = bool(getattr(config, "USE_VIX_DXY", False))
        vix_hard = float(getattr(config, "VIX_HARD_MAX", 30))
        dxy_hard = float(getattr(config, "DXY_PC5_HARD", 2.0))
    except Exception:
        use, vix_hard, dxy_hard = True, 30.0, 2.0

    if not use:
        return None

    if ms.vix_last is not None and ms.vix_last > vix_hard:
        return f"VIX>{vix_hard:.0f}"

    if bias == "LONG" and ms.dxy_pc5 is not None and ms.dxy_pc5 > dxy_hard:
        return f"DXY+5d>{dxy_hard:.1f}%"

    return None

def macro_multiplier(bias: str, ms: MacroState) -> Tuple[float, List[str]]:
    """Ajuste suave del score, acotado por MACRO_SCORE_CAP (±15% por defecto)."""
    try:
        import config
        use = bool(getattr(config, "USE_VIX_DXY", False))
        vix_soft = float(getattr(config, "VIX_SOFT_MAX", 25))
        dxy_warn = float(getattr(config, "DXY_PC5_WARN", 1.0))
        cap = float(getattr(config, "MACRO_SCORE_CAP", 0.15))  # 0.15 => ±15%
    except Exception:
        use, vix_soft, dxy_warn, cap = True, 25.0, 1.0, 0.15

    if not use:
        return 1.0, []

    m = 1.0
    notes: List[str] = []

    # VIX alto ⇒ reduce
    if ms.vix_last is not None and ms.vix_last > vix_soft:
        m *= 0.85
        notes.append(f"VIX {ms.vix_last:.1f}")

    # DXY subida ⇒ penaliza LONG y favorece SHORT
    if ms.dxy_pc5 is not None and ms.dxy_pc5 > dxy_warn:
        if bias == "LONG":
            m *= 0.90
        else:
            m *= 1.05
        notes.append(f"DXY+5d {ms.dxy_pc5:+.1f}%")

    # DXY bajada ⇒ favorece LONG, penaliza SHORT
    if ms.dxy_pc5 is not None and ms.dxy_pc5 < -dxy_warn:
        if bias == "LONG":
            m *= 1.05
        else:
            m *= 0.95
        notes.append(f"DXY+5d {ms.dxy_pc5:+.1f}%")

    # Cap de seguridad
    m = max(1.0 - cap, min(1.0 + cap, m))
    return m, notes
