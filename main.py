# -*- coding: utf-8 -*-
# main.py

import asyncio
import logging
from config import (
    LIMITE_ANALISIS,
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    MIN_SCORE_ALERTA,
)
from utils.path import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_LOG_FILE = LOGS_DIR / "runtime.log"
logging.basicConfig(
    filename=str(RUNTIME_LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8",
    force=True,
)

from data.symbols import obtener_pares_usdt
from logic.analyzer import analizar_simbolo
from logic.reporter import (
    exportar_resultados_excel,
    exportar_resultados_csv,
    imprimir_resumen_terminal,
)
from logic.market_context import obtener_contexto_mercado
from logic.risk_manager import puede_operar
from utils.telegram_utils import enviar_telegram, formatear_senal
from binance.client import Client

async def analizar_todo():
    contexto = obtener_contexto_mercado()
    mensaje_tendencia = (
        f"🌐 BTC: {'Alcista ✅' if contexto.btc_alcista else 'Bajista ❌'} | "
        f"ETH: {'Alcista ✅' if contexto.eth_alcista else 'Bajista ❌'} | "
        f"DXY: {'Alza ✅' if contexto.dxy_alcista else 'Baja ❌'} | "
        f"VIX: {contexto.vix_valor:.1f}"
    )
    enviar_telegram(mensaje_tendencia)
    logging.info("Contexto de mercado obtenido")
    logging.info(f"Score total de contexto: {contexto.score_total}/100")
    if not contexto.apto_long and not contexto.apto_short:
        logging.info("Mercado desfavorable, análisis detenido")
        enviar_telegram("⚠️ Mercado desfavorable. Trading detenido.")
        return
    if not puede_operar():
        logging.info("Operaciones pausadas por control de riesgo")
        enviar_telegram("⏸ Operaciones pausadas por control de riesgo.")
        return
    btc_alcista = contexto.btc_alcista
    eth_alcista = contexto.eth_alcista

    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    symbols = obtener_pares_usdt(client)
    symbols = symbols if LIMITE_ANALISIS is None else symbols[:LIMITE_ANALISIS]
    logging.info(f"Comenzando análisis de {len(symbols)} símbolos")
    resultados = []
    max_score = None

    for sym in symbols:
        logging.info(f"Analizando {sym}")
        try:
            klines_d = client.get_klines(
                symbol=sym,
                interval=Client.KLINE_INTERVAL_1DAY,
                limit=210,
            )
