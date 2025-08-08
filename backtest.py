"""Modulo para ejecutar backtests simples sobre datos historicos."""
from __future__ import annotations

import os
from utils.logger import setup_logging

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)

from datetime import datetime
from typing import Iterable, Dict, List

import pandas as pd
import ta
from binance.client import Client

import config
from logic.longterm import valida_entrada_largo_plazo
from logic.risk_manager import niveles_atr
from utils.data_loader import descargar_klines
from utils.file_manager import append_csv
from utils.path import OUTPUT_DIR

BACKTEST_DIR = OUTPUT_DIR / "backtests"


def _simular_operaciones(symbol: str, client: Client, limite: int = 500) -> List[Dict]:
    """Genera operaciones simuladas para ``symbol`` usando datos diarios."""
    df_d = descargar_klines(symbol, Client.KLINE_INTERVAL_1DAY, limite, client)
    df_w = descargar_klines(symbol, Client.KLINE_INTERVAL_1WEEK, limite // 7 + 10, client)
    operaciones: List[Dict] = []
    for i in range(60, len(df_d) - 1):
        hist_d = df_d.iloc[: i + 1]
        hist_w = df_w.iloc[: i // 7 + 1]
        valido, motivo = valida_entrada_largo_plazo(hist_d, hist_w)
        if not valido:
            continue
        precio = hist_d[4].iloc[-1]
        atr = ta.volatility.AverageTrueRange(hist_d[2], hist_d[3], hist_d[4], 14).average_true_range().iloc[-1]
        tipo = "LONG" if "alcista" in motivo.lower() else "SHORT"
        sl, tp = niveles_atr(precio, atr, tipo)
        salida_idx = i
        salida_precio = precio
        for j in range(i + 1, len(df_d)):
            hi = df_d[2].iloc[j]
            lo = df_d[3].iloc[j]
            if tipo == "LONG":
                if hi >= tp:
                    salida_precio = tp
                    salida_idx = j
                    break
                if lo <= sl:
                    salida_precio = sl
                    salida_idx = j
                    break
            else:
                if lo <= tp:
                    salida_precio = tp
                    salida_idx = j
                    break
                if hi >= sl:
                    salida_precio = sl
                    salida_idx = j
                    break
        duracion = salida_idx - i
        pnl = salida_precio - precio if tipo == "LONG" else precio - salida_precio
        riesgo = abs(precio - sl)
        rr_obtenido = pnl / riesgo if riesgo else 0.0
        operaciones.append(
            {
                "symbol": symbol,
                "tipo": tipo,
                "entrada": datetime.fromtimestamp(df_d[0].iloc[i] / 1000).strftime("%Y-%m-%d"),
                "salida": datetime.fromtimestamp(df_d[0].iloc[salida_idx] / 1000).strftime("%Y-%m-%d"),
                "pnl": round(pnl, 4),
                "rr": round(rr_obtenido, 2),
                "duracion": duracion,
            }
        )
    return operaciones


def _guardar_operaciones(ops: Iterable[Dict]) -> None:
    """Persist e cada operacion en CSV."""
    archivo = BACKTEST_DIR / "trades.csv"
    for op in ops:
        fila = [
            op["symbol"],
            op["tipo"],
            op["entrada"],
            op["salida"],
            str(op["pnl"]),
            str(op["rr"]),
            str(op["duracion"]),
        ]
        append_csv(fila, archivo)


def _guardar_resumen(ops: Iterable[Dict]) -> None:
    df = pd.DataFrame(list(ops))
    if df.empty:
        return
    resumen = df.groupby("symbol").agg(
        operaciones=("pnl", "count"),
        ganadoras=("pnl", lambda x: (x > 0).sum()),
        perdedoras=("pnl", lambda x: (x <= 0).sum()),
        pnl_total=("pnl", "sum"),
        rr_media=("rr", "mean"),
        duracion_media=("duracion", "mean"),
    )
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(BACKTEST_DIR / "summary.csv")


def ejecutar_backtest(simbolos: Iterable[str]) -> None:
    client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
    todas: List[Dict] = []
    for sym in simbolos:
        todas.extend(_simular_operaciones(sym, client))
    _guardar_operaciones(todas)
    _guardar_resumen(todas)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python backtest.py SYMBOL [SYMBOL...]")
        sys.exit(0)
    ejecutar_backtest(sys.argv[1:])
