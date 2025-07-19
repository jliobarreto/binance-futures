# main.py

import asyncio
from config import LIMITE_ANALISIS
from data.symbols import obtener_pares_usdt
from logic.analisis import analizar_simbolo
from logic.sentimiento import tendencia_mercado_global
from utils.telegram import enviar_telegram
import pandas as pd
from datetime import datetime

async def analizar_todo():
    btc_alcista, eth_alcista = tendencia_mercado_global()
    enviar_telegram(f"🌐 Tendencia BTC: {'Alcista ✅' if btc_alcista else 'Bajista ❌'} | ETH: {'Alcista ✅' if eth_alcista else 'Bajista ❌'}")

    symbols = obtener_pares_usdt()
    resultados = []

    for sym in symbols[:LIMITE_ANALISIS]:
        try:
            resultado = await analizar_simbolo(sym, btc_alcista, eth_alcista)
            if resultado:
                resultados.append(resultado)
                if resultado["Mensaje Telegram"]:
                    enviar_telegram(resultado["Mensaje Telegram"])
        except Exception as e:
            print(f"❌ Error con {sym}: {e}")

    # Guardar resultados
    if resultados:
        df = pd.DataFrame(resultados)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        df.to_excel(f"output/señales_long_short_{timestamp}.xlsx", index=False)
        print("✅ Análisis completado y archivo generado.")
    else:
        print("⚠️ No se encontraron señales suficientes.")

if __name__ == "__main__":
    asyncio.run(analizar_todo())