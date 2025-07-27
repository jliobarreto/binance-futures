from __future__ import annotations

from data.models import IndicadoresTecnicos


def calcular_score(tec: IndicadoresTecnicos) -> tuple[float, dict[str, float]]:
    """Return a basic score for a set of technical indicators.

    This implementation is intentionally simple and serves as a
    placeholder so that the rest of the system can run.
    """
    factors = {
        "trend": 20.0,
        "volume": 20.0,
        "momentum": 20.0,
        "volatility": 20.0,
        "risk_reward": 20.0,
    }
    total = sum(factors.values())
    return total, factors
