import pandas as pd
import ta


def valida_entrada_largo_plazo(df_d: pd.DataFrame, df_w: pd.DataFrame) -> tuple[bool, str]:
    """Valida la entrada en marco diario y semanal para operaciones de largo plazo.

    Se confirma que la tendencia semanal y diaria coinciden usando EMAs de 50 y
    200 periodos. Retorna ``(True, motivo)`` si la dirección es clara y
    ``(False, motivo)`` en caso contrario.
    """
    if df_d.empty or df_w.empty:
        return False, "Datos insuficientes"

    close_d = df_d[4].astype(float)
    close_w = df_w[4].astype(float)

    ema50_w = ta.trend.EMAIndicator(close_w, 50).ema_indicator().iloc[-1]
    ema200_w = ta.trend.EMAIndicator(close_w, 200).ema_indicator().iloc[-1]
    ema50_d = ta.trend.EMAIndicator(close_d, 50).ema_indicator().iloc[-1]
    ema200_d = ta.trend.EMAIndicator(close_d, 200).ema_indicator().iloc[-1]
    precio = close_d.iloc[-1]

    # Tendencia alcista de largo plazo
    if ema50_w > ema200_w and precio > ema200_d and ema50_d > ema200_d:
        return True, "Tendencia alcista confirmada"

    # Tendencia bajista de largo plazo
    if ema50_w < ema200_w and precio < ema200_d and ema50_d < ema200_d:
        return True, "Tendencia bajista confirmada"

    return False, "Tendencia de largo plazo indefinida"
