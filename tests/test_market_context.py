import pandas as pd
from logic.market_context import _tendencia_alcista, calcular_score_contexto


def test_tendencia_alcista_true():
    serie = pd.Series(range(1, 301))
    assert _tendencia_alcista(serie) is True


def test_tendencia_alcista_false():
    serie = pd.Series(range(300, 0, -1))
    assert _tendencia_alcista(serie) is False


def test_calcular_score_contexto():
    assert calcular_score_contexto(True, True, False, 15) == 100
    assert calcular_score_contexto(False, False, True, 30) == 0
    assert calcular_score_contexto(True, False, True, 22) == 45
