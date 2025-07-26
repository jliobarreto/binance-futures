import pandas as pd
import numpy as np
import ta


def calcular_indicadores(df: pd.DataFrame) -> dict:
    """Calcula indicadores clave y devuelve un resumen con score."""
    resultado = {
        "score": 0,
        "detalles": {},
        "apto": False,
        "tipo": None,
    }

    if df is None or len(df) < 60:
        resultado["detalles"]["data"] = "Insuficiente"
        return resultado

    df = df.copy()
    df["EMA20"] = ta.trend.ema_indicator(df["close"], window=20)
    df["EMA50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["RSI"] = ta.momentum.rsi(df["close"], window=14)
    df["VOLUMEN_PROMEDIO"] = df["volume"].rolling(window=20).mean()
    df["ATR"] = ta.volatility.average_true_range(
        df["high"], df["low"], df["close"], window=14
    )

    ema20 = df["EMA20"].iloc[-1]
    ema50 = df["EMA50"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    volumen = df["volume"].iloc[-1]
    volumen_prom = df["VOLUMEN_PROMEDIO"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    # === 1. Tendencia EMA ===
    if ema20 > ema50:
        resultado["score"] += 20
        resultado["detalles"]["ema"] = "EMA20 > EMA50 (alcista)"
        resultado["tipo"] = "long"
    elif ema20 < ema50:
        resultado["score"] += 20
        resultado["detalles"]["ema"] = "EMA20 < EMA50 (bajista)"
        resultado["tipo"] = "short"
    else:
        resultado["detalles"]["ema"] = "Cruce neutral"

    # === 2. RSI ===
    if rsi > 55 and resultado["tipo"] == "long":
        resultado["score"] += 20
        resultado["detalles"]["rsi"] = f"RSI {rsi:.2f} (fuerte long)"
    elif rsi < 45 and resultado["tipo"] == "short":
        resultado["score"] += 20
        resultado["detalles"]["rsi"] = f"RSI {rsi:.2f} (fuerte short)"
    else:
        resultado["detalles"]["rsi"] = f"RSI {rsi:.2f} (neutral)"

    # === 3. Volumen ===
    if volumen > volumen_prom:
        resultado["score"] += 20
        resultado["detalles"]["volumen"] = f"Volumen creciente ({volumen:.2f})"
    else:
        resultado["detalles"]["volumen"] = f"Volumen bajo ({volumen:.2f})"

    # === 4. Consolidación y ruptura ===
    df["max20"] = df["high"].rolling(window=20).max()
    df["min20"] = df["low"].rolling(window=20).min()
    rango = df["max20"].iloc[-2] - df["min20"].iloc[-2]
    breakout = df["close"].iloc[-1] > df["max20"].iloc[-2]

    if rango / df["close"].iloc[-2] < 0.05 and breakout and resultado["tipo"] == "long":
        resultado["score"] += 25
        resultado["detalles"]["ruptura"] = "Ruptura alcista tras consolidación"
    elif rango / df["close"].iloc[-2] < 0.05 and df["close"].iloc[-1] < df["min20"].iloc[-2] and resultado["tipo"] == "short":
        resultado["score"] += 25
        resultado["detalles"]["ruptura"] = "Ruptura bajista tras consolidación"
    else:
        resultado["detalles"]["ruptura"] = "Sin ruptura clara"

    # === 5. ATR ===
    if atr > 0:
        resultado["score"] += 15
        resultado["detalles"]["atr"] = f"ATR saludable: {atr:.4f}"
    else:
        resultado["detalles"]["atr"] = f"ATR bajo: {atr:.4f}"

    resultado["apto"] = resultado["score"] >= 65
    return resultado
