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
from logic.sentiment import tendencia_mercado_global
from utils.telegram_utils import enviar_telegram
from binance.client import Client

async def analizar_todo():
    btc_alcista, eth_alcista = tendencia_mercado_global()
    enviar_telegram(f"🌐 Tendencia BTC: {'Alcista ✅' if btc_alcista else 'Bajista ❌'} | ETH: {'Alcista ✅' if eth_alcista else 'Bajista ❌'}")

    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    symbols = obtener_pares_usdt(client)
    symbols = symbols if LIMITE_ANALISIS is None else symbols[:LIMITE_ANALISIS]
    resultados = []
    max_score = None

    for sym in symbols:
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
            resultado = analizar_simbolo(sym, klines_d, klines_w, btc_alcista, eth_alcista)
            if resultado:
                tec, score, _ = resultado
                if max_score is None or score > max_score:
                    max_score = score
                if score >= MIN_SCORE_ALERTA:
                    resultados.append({
                        "Criptomoneda": sym,
                        "Señal": tec.tipo,
                        "Precio": tec.precio,
                        "TP": tec.tp,
                        "SL": tec.sl,
                        "Score": score,
                    })
        except Exception as e:
            logging.error(f"Error analizando {sym}: {e}")

    archivo_excel = exportar_resultados_excel(resultados)
    archivo_csv = exportar_resultados_csv(resultados)
    imprimir_resumen_terminal(resultados, evaluados=len(symbols), score_max=max_score)
    if archivo_excel:
        enviar_telegram(f"📂 Archivo generado: {archivo_excel}")
    if archivo_csv:
        enviar_telegram(f"📂 Archivo generado: {archivo_csv}")


if __name__ == "__main__":
    asyncio.run(analizar_todo())
