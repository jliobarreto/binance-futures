"""Herramientas básicas de gestión de riesgo.

Este módulo calcula el tamaño de posición según el riesgo
permitido y permite generar niveles automáticos de stop loss y
objetivos en función del ATR.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskParameters:
    capital_total: float
    riesgo_pct: float = 0.02  # porcentaje de riesgo por operación
    atr_multiplicador_sl: float = 1.5
    atr_multiplicador_tp: float = 3.0


def calcular_tamano_posicion(capital: float, entrada: float, sl: float, riesgo_pct: float) -> float:
    """Calcula la cantidad de unidades a comprar o vender.

    Parameters
    ----------
    capital: float
        Capital disponible en la cuenta.
    entrada: float
        Precio de entrada de la operación.
    sl: float
        Nivel de stop loss.
    riesgo_pct: float
        Porcentaje del capital a arriesgar.
    """
    riesgo_monetario = capital * riesgo_pct
    riesgo_por_unidad = abs(entrada - sl)
    if riesgo_por_unidad == 0:
        return 0.0
    return riesgo_monetario / riesgo_por_unidad


def niveles_atr(precio: float, atr: float, tipo: str, multip_sl: float = 1.5, multip_tp: float = 3.0) -> tuple[float, float]:
    """Genera niveles de SL y TP usando el ATR como referencia."""
    if tipo.upper() == "LONG":
        sl = precio - multip_sl * atr
        tp = precio + multip_tp * atr
    else:
        sl = precio + multip_sl * atr
        tp = precio - multip_tp * atr
    return sl, tp
