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
    """Descarga precios históricos usando :mod:`yfinance` con reintentos."""
    for _ in range(3):
        try:
            df = yf.download(
                ticker,
                interval=interval,
                period=period,
                progress=False,
                auto_adjust=False,
            )
            return df
        except Exception as exc:  # pragma: no cover - dependencias externas
            logging.warning(f"No se pudieron obtener datos para {ticker} {interval}: {exc}")
            time.sleep(1)
    return pd.DataFrame()


def _tendencia_alcista(close: pd.Series | pd.DataFrame) -> bool:
    """Valida si una serie está en tendencia alcista usando EMAs.

    Se asegura que ``close`` sea una :class:`~pandas.Series` y que exista
    un historial suficiente (al menos 200 velas) para calcular las EMAs de
    50 y 200 periodos.  Retorna ``True`` cuando la EMA50 se encuentra por
    encima de la EMA200 y el precio de cierre está sobre la EMA50.
    """

    if isinstance(close, pd.DataFrame):
        close = close.squeeze()

    if not isinstance(close, pd.Series) or len(close) < 200:
        return False

    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1]
    return ema50 > ema200 and close.iloc[-1] > ema50


def calcular_score_contexto(
    btc_alcista: bool, eth_alcista: bool, dxy_alcista: bool, vix_valor: float
) -> float:
    """Asigna un puntaje de 0 a 100 al contexto macro.

    Los puntajes se distribuyen de la siguiente manera:

    - 40 puntos si BTC está en tendencia alcista.
    - 30 puntos si ETH está en tendencia alcista.
    - 20 puntos si el DXY está bajista.
    - 10 puntos adicionales si el VIX es menor a 20, o 5 si está entre 20 y 25.
    """

    score = 0.0
    score += 40 if btc_alcista else 0.0
    score += 30 if eth_alcista else 0.0
    score += 20 if not dxy_alcista else 0.0
    if vix_valor < 20:
        score += 10
    elif vix_valor < 25:
        score += 5
    return score

def obtener_contexto_mercado() -> ContextoMercado:
    btc_d = _descargar_datos("BTC-USD", "1d")
    btc_w = _descargar_datos("BTC-USD", "1wk")
    eth_d = _descargar_datos("ETH-USD", "1d")
    eth_w = _descargar_datos("ETH-USD", "1wk")
    dxy_d = _descargar_datos("DX-Y.NYB", "1d")
    vix_d = _descargar_datos("^VIX", "1d")

    if btc_d.empty or btc_w.empty or eth_d.empty or eth_w.empty or dxy_d.empty or vix_d.empty:
        logging.error("Fallo la descarga de datos de mercado. Contexto incompleto")

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

    btc_ema20_w = (
        float(ta.trend.EMAIndicator(btc_close_w, 20).ema_indicator().iloc[-1])
        if not btc_w.empty
        else 0.0
    )
    btc_ema50_w = (
        float(ta.trend.EMAIndicator(btc_close_w, 50).ema_indicator().iloc[-1])
        if not btc_w.empty
        else 0.0
    )
    btc_rsi_w = (
        float(ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1])
        if len(btc_close_w) >= 14
        else 0.0
    )

    eth_ema20_d = (
        float(ta.trend.EMAIndicator(eth_close_d, 20).ema_indicator().iloc[-1])
        if not eth_d.empty
        else 0.0
    )
    eth_ema50_d = (
        float(ta.trend.EMAIndicator(eth_close_d, 50).ema_indicator().iloc[-1])
        if not eth_d.empty
        else 0.0
    )
    eth_rsi_d = (
        float(ta.momentum.RSIIndicator(eth_close_d, 14).rsi().iloc[-1])
        if len(eth_close_d) >= 14
        else 0.0
    )

    btc_alcista = _tendencia_alcista(btc_close_d) and _tendencia_alcista(btc_close_w)
    eth_alcista = _tendencia_alcista(eth_close_d) and _tendencia_alcista(eth_close_w)
    dxy_alcista = _tendencia_alcista(dxy_close_d)
    vix_valor = float(vix_close.iloc[-1].item()) if not vix_close.empty else 0.0

    logging.debug(
        f"Tendencias: BTC_alcista={btc_alcista}, ETH_alcista={eth_alcista}, "
        f"DXY_alcista={dxy_alcista}, VIX={vix_valor:.2f}"
    )

    score_total = calcular_score_contexto(btc_alcista, eth_alcista, dxy_alcista, vix_valor)
    logging.debug(
        f"Score base contexto: {score_total:.1f} | BTC={btc_alcista}, ETH={eth_alcista}, "
        f"DXY={dxy_alcista}, VIX={vix_valor:.2f}"
    )

    # === Puntuación para operaciones LONG ===
    score_long_btc = 0
    score_long_rsi = 0
    score_long_eth = 0
    score_long_dxy = 0
    log_long: list[str] = []

    if not btc_w.empty:
        ema20 = float(
            ta.trend.EMAIndicator(btc_close_w, 20).ema_indicator().iloc[-1]
        )
        ema50 = float(
            ta.trend.EMAIndicator(btc_close_w, 50).ema_indicator().iloc[-1]
        )
        hl = len(btc_w) >= 2 and btc_w["Low"].iloc[-1] > btc_w["Low"].iloc[-2]
        if hl and ema20 > ema50:
            score_long_btc = 25
        log_long.append(
            f"BTC semanal HL {hl} | EMA20 {ema20:.2f} > EMA50 {ema50:.2f} - Score: {score_long_btc}/25"
        )

        rsi_w = (
            float(ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1])
            if len(btc_close_w) >= 14
            else 0.0
        )
        vol_up = len(btc_w) >= 2 and btc_w["Volume"].iloc[-1] > btc_w["Volume"].iloc[-2]
        if rsi_w > 50 and vol_up:
            score_long_rsi = 25
        log_long.append(
            f"RSI semanal {rsi_w:.1f} | Volumen creciente {vol_up} - Score: {score_long_rsi}/25"
        )
    else:
        log_long.append("BTC semanal: datos insuficientes - Score: 0/25")
        log_long.append("RSI semanal: datos insuficientes - Score: 0/25")

    if not eth_d.empty:
        vol_up_eth = len(eth_d) >= 2 and eth_d["Volume"].iloc[-1] > eth_d["Volume"].iloc[-2]
        alcista_eth = eth_ema20_d > eth_ema50_d
        if alcista_eth and eth_rsi_d > 50 and vol_up_eth:
            score_long_eth = 25
        log_long.append(
            f"ETH EMA20 {eth_ema20_d:.2f} > EMA50 {eth_ema50_d:.2f} | RSI {eth_rsi_d:.1f} | Volumen up {vol_up_eth} - Score: {score_long_eth}/25"
        )
    else:
        log_long.append("ETH diario sin datos - Score: 0/25")

    dxy_bajista = not _tendencia_alcista(dxy_close_d)
    if dxy_bajista and vix_valor < 20:
        score_long_dxy = 25
    log_long.append(
        f"DXY bajista {dxy_bajista} | VIX {vix_valor:.2f} - Score: {score_long_dxy}/25"
    )

    score_long = score_long_btc + score_long_rsi + score_long_eth + score_long_dxy
    log_long.append(f"Score parcial BTC: {score_long_btc}/25")
    log_long.append(f"Score parcial RSI/Vol: {score_long_rsi}/25")
    log_long.append(f"Score parcial ETH: {score_long_eth}/25")
    log_long.append(f"Score parcial DXY-VIX: {score_long_dxy}/25")

    # === Puntuación para operaciones SHORT ===
    score_short_btc = 0
    score_short_rsi = 0
    score_short_eth = 0
    score_short_dxy = 0
    log_short: list[str] = []

    if not btc_w.empty:
        ema20 = float(
            ta.trend.EMAIndicator(btc_close_w, 20).ema_indicator().iloc[-1]
        )
        ema50 = float(
            ta.trend.EMAIndicator(btc_close_w, 50).ema_indicator().iloc[-1]
        )
        lh = len(btc_w) >= 2 and btc_w["High"].iloc[-1] < btc_w["High"].iloc[-2]
        if lh and ema20 < ema50:
            score_short_btc = 25
        log_short.append(
            f"BTC semanal LH {lh} | EMA20 {ema20:.2f} < EMA50 {ema50:.2f} - Score: {score_short_btc}/25"
        )

        rsi_w = (
            float(ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1])
            if len(btc_close_w) >= 14
            else 0.0
        )
        vol_sell = len(btc_w) >= 2 and btc_w["Volume"].iloc[-1] >= btc_w["Volume"].iloc[-2]
        if rsi_w < 50 and vol_sell:
            score_short_rsi = 25
        log_short.append(
            f"RSI semanal {rsi_w:.1f} | Volumen venta {vol_sell} - Score: {score_short_rsi}/25"
        )
    else:
        log_short.append("BTC semanal: datos insuficientes - Score: 0/25")
        log_short.append("RSI semanal: datos insuficientes - Score: 0/25")

    if not eth_d.empty:
        vol_sell_eth = len(eth_d) >= 2 and eth_d["Volume"].iloc[-1] >= eth_d["Volume"].iloc[-2]
        bajista_eth = eth_ema20_d < eth_ema50_d
        if bajista_eth and eth_rsi_d < 50 and vol_sell_eth:
            score_short_eth = 25
        log_short.append(
            f"ETH EMA20 {eth_ema20_d:.2f} < EMA50 {eth_ema50_d:.2f} | RSI {eth_rsi_d:.1f} | Vol venta {vol_sell_eth} - Score: {score_short_eth}/25"
        )
    else:
        log_short.append("ETH diario sin datos - Score: 0/25")

    dxy_alza = _tendencia_alcista(dxy_close_d)
    if dxy_alza and vix_valor > 20:
        score_short_dxy = 25
    log_short.append(

        log_short.append(
            f"BTC semanal LH {lh} | EMA20 {ema20:.2f} < EMA50 {ema50:.2f} - Score: {score_short_btc}/25"
        )

        rsi_w = ta.momentum.RSIIndicator(btc_close_w, 14).rsi().iloc[-1] if len(btc_close_w) >= 14 else 0.0
        vol_sell = len(btc_w) >= 2 and btc_w["Volume"].iloc[-1] >= btc_w["Volume"].iloc[-2]
        if rsi_w < 50 and vol_sell:
            score_short_rsi = 25
        log_short.append(
            f"RSI semanal {rsi_w:.1f} | Volumen venta {vol_sell} - Score: {score_short_rsi}/25"
        )
    else:
        log_short.append("BTC semanal: datos insuficientes - Score: 0/25")
        log_short.append("RSI semanal: datos insuficientes - Score: 0/25")

    if not eth_d.empty:
        vol_sell_eth = len(eth_d) >= 2 and eth_d["Volume"].iloc[-1] >= eth_d["Volume"].iloc[-2]
        bajista_eth = eth_ema20_d < eth_ema50_d
        if bajista_eth and eth_rsi_d < 50 and vol_sell_eth:
            score_short_eth = 25
        log_short.append(
            f"ETH EMA20 {eth_ema20_d:.2f} < EMA50 {eth_ema50_d:.2f} | RSI {eth_rsi_d:.1f} | Vol venta {vol_sell_eth} - Score: {score_short_eth}/25"
        )
    else:
        log_short.append("ETH diario sin datos - Score: 0/25")

    dxy_alza = _tendencia_alcista(dxy_close_d)
    if dxy_alza and vix_valor > 20:
        score_short_dxy = 25
    log_short.append(
        f"DXY alcista {dxy_alza} | VIX {vix_valor:.2f} - Score: {score_short_dxy}/25"
    )

    score_short = score_short_btc + score_short_rsi + score_short_eth + score_short_dxy
    log_short.append(f"Score parcial BTC: {score_short_btc}/25")
    log_short.append(f"Score parcial RSI/Vol: {score_short_rsi}/25")
    log_short.append(f"Score parcial ETH: {score_short_eth}/25")
    log_short.append(f"Score parcial DXY-VIX: {score_short_dxy}/25")

    apto_long = score_long >= SCORE_THRESHOLD_LONG
    apto_short = score_short >= SCORE_THRESHOLD_SHORT

    resumen_long = "\n".join("  " + linea for linea in log_long)
    logging.info(
        "[LONG CONTEXT]\n" + resumen_long +
        f"\n  Score global LONG: {score_long:.0f}/100 "
        f"{'→ Apto para operar en largo' if apto_long else '→ No apto para operar en largo'}"
    )

    resumen_short = "\n".join("  " + linea for linea in log_short)
    logging.info(
        "[SHORT CONTEXT]\n" + resumen_short +
        f"\n  Score global SHORT: {score_short:.0f}/100 "
        f"{'→ Apto para operar en corto' if apto_short else '→ No apto para operar en corto'}"
    )

    mercado_favorable = apto_long or apto_short
    if not mercado_favorable:
        logging.info("Mercado desfavorable -> análisis detenido")

    registrar_contexto_csv(
        {
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
