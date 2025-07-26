"""Funciones para calcular el score institucional."""

from config import (
    ATR_MIN,
    ATR_MAX,
    RSI_OVERSOLD,
    RSI_BUY_MIN,
    RSI_BUY_MAX,
    RSI_OVERBOUGHT,
    RSI_WEEKLY_OVERBOUGHT,
)


def calcular_trend_score(tec) -> float:
    """Evalúa la tendencia combinando EMAs y dirección del MACD."""
    score = 0
    if tec.tipo == "LONG":
        if tec.ema20 > tec.ema50 > tec.ema200:
            score += 50
        if tec.macd_1d > tec.macd_signal_1d:
            score += 50
    else:
        if tec.ema20 < tec.ema50 < tec.ema200:
            score += 50
        if tec.macd_1d < tec.macd_signal_1d:
            score += 50
    return score


def calcular_volume_score(tec) -> float:
    """Normaliza el volumen actual respecto al promedio (0-100)."""
    if not tec.volumen_promedio:
        return 0.0
    ratio = tec.volumen_actual / tec.volumen_promedio
    if ratio <= 0.5:
        return 0.0
    if ratio >= 1.5:
        return 100.0
    return (ratio - 0.5) / 1.0 * 100.0


def calcular_momentum_score(tec) -> float:
    """Asigna puntaje basado en RSI diario."""
    rsi = tec.rsi_1d
    if tec.tipo == "LONG":
        if rsi < RSI_OVERSOLD:
            return 100.0
        if rsi < RSI_BUY_MIN:
            return 80.0
        if rsi <= RSI_BUY_MAX:
            return 60.0
        return 40.0
    else:
        if rsi > RSI_OVERBOUGHT:
            return 100.0
        if rsi > RSI_WEEKLY_OVERBOUGHT:
            return 80.0
        if rsi >= 45:
            return 60.0
        return 40.0


def calcular_volatility_score(tec) -> float:
    """Valora el ATR en un rango saludable."""
    if ATR_MIN <= tec.atr <= ATR_MAX:
        return 100.0
    return 0.0


def calcular_rr_score(tec) -> float:
    """Puntaje basado en la relación TP/SL."""
    try:
        rr = abs(tec.tp - tec.precio) / abs(tec.precio - tec.sl)
    except ZeroDivisionError:
        return 0.0
    if rr >= 3:
        return 100.0
    if rr >= 2:
        return 80.0
    if rr >= 1:
        return 50.0
    return 20.0


WEIGHTS = {
    "trend": 0.4,
    "momentum": 0.2,
    "volume": 0.2,
    "volatility": 0.1,
    "risk_reward": 0.1,
}


def calcular_score(tec):
    """Calcula el score total y entrega el detalle de factores."""
    trend = calcular_trend_score(tec)
    momentum = calcular_momentum_score(tec)
    volume = calcular_volume_score(tec)
    volatility = calcular_volatility_score(tec)
    rr = calcular_rr_score(tec)

    score = (
        trend * WEIGHTS["trend"]
        + momentum * WEIGHTS["momentum"]
        + volume * WEIGHTS["volume"]
        + volatility * WEIGHTS["volatility"]
        + rr * WEIGHTS["risk_reward"]
    )

    breakdown = {
        "trend": trend,
        "momentum": momentum,
        "volume": volume,
        "volatility": volatility,
        "risk_reward": rr,
    }
    return round(score, 2), breakdown
