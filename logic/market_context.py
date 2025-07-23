from dataclasses import dataclass
import logging
import pandas as pd
import ta
import yfinance as yf
from config import MIN_SCORE_MERCADO

@dataclass
class ContextoMercado:
    btc_alcista: bool
    eth_alcista: bool
    dxy_alcista: bool
    vix_valor: float
    mercado_favorable: bool

def _descargar_cierre(ticker: str, interval: str, period: str = "400d") -> pd.Series:
    df = yf.download(
        ticker,
        interval=interval,
        period=period,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return pd.Series(dtype=float)
    return df["Close"].astype(float).squeeze("columns")


def _tendencia_alcista(close: pd.Series) -> bool:
    if close.empty or len(close) < 200:
        return False
@@ -54,34 +55,67 @@ def obtener_contexto_mercado() -> ContextoMercado:
        return ContextoMercado(False, False, False, 0.0, False)

    try:
        eth_w = _descargar_cierre("ETH-USD", "1wk")
    except Exception as e:
        logging.error(f"Error descargando ETH-USD 1wk: {e}")
        return ContextoMercado(False, False, False, 0.0, False)

    try:
        dxy_d = _descargar_cierre("^DXY", "1d")
    except Exception as e:
        logging.error(f"Error descargando ^DXY 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False)

    try:
        vix_d = _descargar_cierre("^VIX", "1d", "100d")
    except Exception as e:
        logging.error(f"Error descargando ^VIX 1d: {e}")
        return ContextoMercado(False, False, False, 0.0, False)

    btc_alcista = _tendencia_alcista(btc_d) and _tendencia_alcista(btc_w)
    eth_alcista = _tendencia_alcista(eth_d) and _tendencia_alcista(eth_w)
    dxy_alcista = _tendencia_alcista(dxy_d)
    vix_valor = float(vix_d.iloc[-1]) if not vix_d.empty else 0.0

    # Razones descriptivas para el registro
    btc_reason = (
        "EMA50>EMA200 y precio>EMA50" if btc_alcista else "EMA50<EMA200 o precio<EMA50"
    )
    eth_reason = (
        "EMA50>EMA200 y precio>EMA50" if eth_alcista else "EMA50<EMA200 o precio<EMA50"
    )
    dxy_reason = (
        "DXY en tendencia bajista" if not dxy_alcista else "DXY en tendencia alcista"
    )
    vix_reason = (
        "volatilidad elevada" if vix_valor >= 20 else "volatilidad controlada"
    )

    score_total = (
        (25 if btc_alcista else 0)
        + (25 if eth_alcista else 0)
        + (25 if not dxy_alcista else 0)
        + (25 if vix_valor < 25 else 0)
    )
    mercado_favorable = score_total >= MIN_SCORE_MERCADO

    logging.info(
        "Contexto macro | "
        f"BTC: {'alcista' if btc_alcista else 'bajista'} → {btc_reason} | "
        f"ETH: {'alcista' if eth_alcista else 'bajista'} → {eth_reason} | "
        f"DXY: {'alcista' if dxy_alcista else 'bajista'} → {dxy_reason} | "
        f"VIX: {vix_valor:.1f} → {vix_reason}"
    )
    logging.info(
        f"Score de contexto: {score_total}/100 - Umbral requerido: {MIN_SCORE_MERCADO}"
    )
    if not mercado_favorable:
        logging.info("Contexto desfavorable")

    return ContextoMercado(
        btc_alcista=btc_alcista,
        eth_alcista=eth_alcista,
        dxy_alcista=dxy_alcista,
        vix_valor=vix_valor,
        mercado_favorable=mercado_favorable,
    )
