"""Validación de estructuras de consolidación y rupturas."""

from __future__ import annotations

import pandas as pd


def ruptura_confirmada(df: pd.DataFrame, periodo: int = 20, umbral: float = 0.02) -> bool:
    """Evalúa si existe una ruptura válida tras un periodo de consolidación.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos OHLC con columnas 0:open, 1:high, 2:low, 3:close.
    periodo : int
        Número de velas para medir la consolidación previa.
    umbral : float
        Porcentaje de ruptura respecto al rango de consolidación.
    """
    if len(df) < periodo + 1:
        return False

    cierre = df[4]
    maximo = cierre.iloc[-periodo - 1:-1].max()
    minimo = cierre.iloc[-periodo - 1:-1].min()
    rango = maximo - minimo
    if rango == 0:
        return False

    ultimo = cierre.iloc[-1]
    ruptura = ultimo > maximo * (1 + umbral) or ultimo < minimo * (1 - umbral)
    return ruptura
