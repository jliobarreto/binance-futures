# main.py

import asyncio
from config import (
    LIMITE_ANALISIS,
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
)
from data.symbols import obtener_pares_usdt
from logic.analyzer import analizar_simbolo
from logic.reporter import exportar_resultados_excel, imprimir_resumen_terminal
from logic.sentimiento import tendencia_mercado_global
from utils.telegram import enviar_telegram
from binance.client import Client
from datetime import datetime

async def analizar_todo():
    btc_alcista, eth_alcista = tendencia_mercado_global()
    enviar_telegram(f"🌐 Tendencia BTC: {'Alcista ✅' if btc_alcista else 'Bajista ❌'} | ETH: {'Alcista ✅' if eth_alcista else 'Bajista ❌'}")

    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    symbols = obtener_pares_usdt(client)
    resultados = []

    for sym in symbols[:LIMITE_ANALISIS]:
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

            analisis = analizar_simbolo(sym, klines_d, klines_w, btc_alcista, eth_alcista)
            if analisis:
                tec, score, notes = analisis
                resultados.append(
                    {
                        "Criptomoneda": tec.symbol,
                        "Señal": tec.tipo,
                        "Precio": tec.precio,
                        "TP": tec.tp,
                        "SL": tec.sl,
                        "Score": score,
                        "Notas": "; ".join(notes),
                    }
                )
        except Exception as e:
            print(f"❌ Error con {sym}: {e}")

    # Guardar resultados
    if resultados:
        archivo = exportar_resultados_excel(resultados)
        imprimir_resumen_terminal(resultados)
        print(f"✅ Resultados guardados en: {archivo}")
    else:
        imprimir_resumen_terminal(resultados)


if __name__ == "__main__":
    asyncio.run(analizar_todo())
    