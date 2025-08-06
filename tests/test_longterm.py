+39
-0

import pandas as pd

from logic.longterm import valida_entrada_largo_plazo


def _build_df(close_values):
    data = {
        0: list(range(len(close_values))),
        1: close_values,
        2: close_values,
        3: close_values,
        4: close_values,
        5: [1] * len(close_values),
    }
    return pd.DataFrame(data).astype(float)


def test_valida_entrada_largo_plazo_valido():
    df_d = _build_df(range(1, 300))
    df_w = _build_df([1, 2] * 40)
    es_valido, motivo = valida_entrada_largo_plazo(df_d, df_w)
    assert es_valido is True
    assert motivo == ""


def test_valida_entrada_largo_plazo_rsi_invalido():
    df_d = _build_df(range(1, 300))
    df_w = _build_df(range(1, 80))
    es_valido, motivo = valida_entrada_largo_plazo(df_d, df_w)
    assert es_valido is False
    assert "RSI" in motivo


def test_valida_entrada_largo_plazo_ema_invalido():
    df_d = _build_df(range(300, 0, -1))
    df_w = _build_df([1, 2] * 40)
    es_valido, motivo = valida_entrada_largo_plazo(df_d, df_w)
    assert es_valido is False
    assert "Tendencia" in motivo
