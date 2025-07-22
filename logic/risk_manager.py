"""Herramientas básicas de gestión de riesgo.

Este módulo calcula el tamaño de posición según el riesgo
permitido y permite generar niveles automáticos de stop loss y
objetivos en función del ATR.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import yfinance as yf

from config import (
    MAX_CONSEC_LOSSES,
    BTC_DROP_THRESHOLD,
    VOLUME_DROP_THRESHOLD,
    TRADE_HISTORY_FILE,
)
from utils.file_manager import append_csv


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


def registrar_resultado(pnl: float) -> None:
    """Registra el resultado de una operación en el historial."""
    fila = [datetime.utcnow().isoformat(timespec="seconds"), f"{pnl:.2f}"]
    append_csv(fila, TRADE_HISTORY_FILE)


def _leer_historial() -> list[float]:
    if not Path(TRADE_HISTORY_FILE).exists():
        return []
    pnls: list[float] = []
    with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            try:
                pnls.append(float(parts[1]))
            except ValueError:
                continue
    return pnls


def _perdidas_consecutivas(hist: list[float]) -> int:
    count = 0
    for pnl in reversed(hist):
        if pnl < 0:
            count += 1
        else:
            break
    return count


def puede_operar() -> bool:
    """Determina si se permite abrir nuevas operaciones."""
    if _perdidas_consecutivas(_leer_historial()) >= MAX_CONSEC_LOSSES:
        return False

    try:
        btc = yf.download(
            "BTC-USD",
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
       btc = yf.download("BTC-USD", period="2d", interval="1d", progress=False)
        if not btc.empty:
            apertura = float(btc["Open"].iloc[-1])
            cierre = float(btc["Close"].iloc[-1])
            if apertura and (cierre - apertura) / apertura <= -BTC_DROP_THRESHOLD:
                return False
    except Exception:
        pass

    try:
        total = yf.download(
            "TOTAL",
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        total = yf.download("TOTAL", period="2d", interval="1d", progress=False)
        if "Volume" in total.columns and len(total) >= 2:
            vol_prev = float(total["Volume"].iloc[-2])
            vol_act = float(total["Volume"].iloc[-1])
            if vol_prev and (vol_act - vol_prev) / vol_prev <= -VOLUME_DROP_THRESHOLD:
                return False
    except Exception:
        pass

    return True
