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
logging.basicConfig(
    filename=LOGS_DIR / "runtime.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
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
    if not contexto.mercado_favorable:
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
            klines_w = client.get_klines(
                symbol=sym,
                interval=Client.KLINE_INTERVAL_1WEEK,
                limit=210,
            )
            logging.debug(
                f"{sym} datos diarios: {len(klines_d)} velas, semanales: {len(klines_w)}"
            )
            resultado = analizar_simbolo(sym, klines_d, klines_w, btc_alcista, eth_alcista)
            logging.info(f"Análisis de {sym} completado")
            if resultado:
                tec, score, _ = resultado
                if max_score is None or score > max_score:
                    max_score = score
                resultado_dict = {
                    "Criptomoneda": tec.symbol,
                    "Señal": tec.tipo,
                    "Precio": tec.precio,
                    "TP": tec.tp,
                    "SL": tec.sl,
                    "RSI": tec.rsi_1d,
                    "MACD": tec.macd_1d,
                    "MACD_signal": tec.macd_signal_1d,
                    "Vitalidad": tec.volumen_actual / tec.volumen_promedio if tec.volumen_promedio else None,
                    "Grids": tec.grids,
                    "Score": score,
                }
                resultados.append(resultado_dict)
                logging.debug(f"Resultado de {sym}: {resultado_dict}")
                mensaje_senal = formatear_senal(resultado_dict)
                enviar_telegram(mensaje_senal)
        except Exception as e:
            logging.error(f"Error analizando {sym}: {e}")

    archivo_excel = exportar_resultados_excel(resultados)
