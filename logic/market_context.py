# -*- coding: utf-8 -*-
"""Market context evaluation utilities.

Este módulo calcula el contexto de mercado en función de diversos
indicadores macro y evalúa de forma diferenciada las condiciones para
operar en **largo** o en **corto**.  Cada dirección obtiene un puntaje de
0 a 100 basado en varios factores técnicos y de sentimiento.
"""

from dataclasses import dataclass
import logging
from datetime import datetime
import pandas as pd
import ta
import yfinance as yf
import time
from logic.reporter import registrar_contexto_csv
try:  # Permite ejecutar este módulo directamente desde la carpeta logic
    from config import SCORE_THRESHOLD_LONG, SCORE_THRESHOLD_SHORT
except ModuleNotFoundError:  # pragma: no cover - ajuste para entornos fuera del paquete
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import SCORE_THRESHOLD_LONG, SCORE_THRESHOLD_SHORT


@dataclass
class ContextoMercado:
    btc_alcista: bool
    eth_alcista: bool
    dxy_alcista: bool
    vix_valor: float
    mercado_favorable: bool
    score_total: float
    score_long: float = 0.0
    score_short: float = 0.0
    apto_long: bool = False
    apto_short: bool = False

def _descargar_datos(ticker: str, interval: str, period: str = "400d") -> pd.DataFrame:
    """Descarga precios históricos usando :mod:`yfinance` con reintentos.

    Si ``interval`` es ``"1wk"`` se descargan ~5 años por defecto para poder
    calcular indicadores de largo plazo como la EMA200.
    """

    if interval == "1wk" and period == "400d":
        period = "260wk"

    for _ in range(3):
        try:
            df = yf.download(
                ticker,
                interval=interval,
                period=period,
                progress=False,
                auto_adjust=False,
            )
            if interval == "1wk" and len(df) < 200:
                df = yf.download(
                    ticker,
                    interval=interval,
                    period="max",
                    progress=False,
                    auto_adjust=False,
                )
            return df
        except Exception as e:  # pragma: no cover - dependencias externas
            logging.warning(f"Error descargando {ticker} {interval}: {e}")
            time.sleep(1)
    return pd.DataFrame()
def obtener_contexto_mercado() -> ContextoMercado:
    btc_d = _descargar_datos("BTC-USD", "1d")
    btc_w = _descargar_datos("BTC-USD", "1wk")
    eth_d = _descargar_datos("ETH-USD", "1d")
    eth_w = _descargar_datos("ETH-USD", "1wk")
    dxy_d = _descargar_datos("DX-Y.NYB", "1d")
    vix_d = _descargar_datos("^VIX", "1d")

    btc_close_d = (
        btc_d["Close"].astype(float).squeeze() if "Close" in btc_d else pd.Series(dtype=float)
    )
    logging.debug(f"BTC close 1d último valor: {btc_close_d.iloc[-1] if not btc_close_d.empty else 'N/A'}")
    btc_close_w = (
        btc_w["Close"].astype(float).squeeze() if "Close" in btc_w else pd.Series(dtype=float)
    )
    logging.debug(f"BTC close 1w último valor: {btc_close_w.iloc[-1] if not btc_close_w.empty else 'N/A'}")
    eth_close_d = (
        eth_d["Close"].astype(float).squeeze() if "Close" in eth_d else pd.Series(dtype=float)
    )
    logging.debug(f"ETH close 1d último valor: {eth_close_d.iloc[-1] if not eth_close_d.empty else 'N/A'}")
    eth_close_w = (
        eth_w["Close"].astype(float).squeeze() if "Close" in eth_w else pd.Series(dtype=float)
    )
    logging.debug(f"ETH close 1w último valor: {eth_close_w.iloc[-1] if not eth_close_w.empty else 'N/A'}")
    dxy_close_d = (
        dxy_d["Close"].astype(float).squeeze() if "Close" in dxy_d else pd.Series(dtype=float)
    )
    logging.debug(f"DXY close 1d último valor: {dxy_close_d.iloc[-1] if not dxy_close_d.empty else 'N/A'}")
    vix_close = (
        vix_d["Close"].astype(float).squeeze() if "Close" in vix_d else pd.Series(dtype=float)
    )
    logging.debug(f"VIX close 1d último valor: {vix_close.iloc[-1] if not vix_close.empty else 'N/A'}")

@@ -219,25 +257,36 @@ def obtener_contexto_mercado() -> ContextoMercado:
            "fecha": datetime.utcnow().isoformat(timespec="seconds"),
            "score_long": f"{score_long:.1f}",
            "score_short": f"{score_short:.1f}",
            "VIX": f"{vix_valor:.2f}",
            "BTC_EMA20": f"{btc_ema20_w:.2f}",
            "BTC_EMA50": f"{btc_ema50_w:.2f}",
            "BTC_RSI": f"{btc_rsi_w:.2f}",
            "ETH_EMA20": f"{eth_ema20_d:.2f}",
            "ETH_EMA50": f"{eth_ema50_d:.2f}",
            "ETH_RSI": f"{eth_rsi_d:.2f}",
        }
    )

    return ContextoMercado(
        btc_alcista=btc_alcista,
        eth_alcista=eth_alcista,
        dxy_alcista=dxy_alcista,
        vix_valor=vix_valor,
        mercado_favorable=mercado_favorable,
        score_total=score_total,
        score_long=score_long,
        score_short=score_short,
        apto_long=apto_long,
        apto_short=apto_short,
    )


def _tendencia_alcista(close: pd.Series) -> bool:
    """Evalúa tendencia alcista usando EMAs de 50 y 200 periodos."""

    if len(close) < 200:
        return False

    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1]
    return ema50 > ema200
