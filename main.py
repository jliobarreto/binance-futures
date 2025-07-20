# main.py

import asyncio
from config import (
    LIMITE_ANALISIS,
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
)
from data.symbols import obtener_pares_usdt
from logic.analyzer import analizar_simbolo
from logic.sentimiento import tendencia_mercado_global
from utils.telegram import enviar_telegram
from binance.client import Client
import pandas as pd
from datetime import datetime

async def analizar_todo():
    btc_alcista, eth_alcista = tendencia_mercado_global()
    enviar_telegram(f"🌐 Tendencia BTC: {'Alcista ✅' if btc_alcista else 'Bajista ❌'} | ETH: {'Alcista ✅' if eth_alcista else 'Bajista ❌'}")

    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    symbols = obtener_pares_usdt(client)
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