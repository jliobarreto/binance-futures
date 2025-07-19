# data/symbols.py

from binance.client import Client
from config import EXCLUDED_TERMS

def obtener_pares_usdt(client: Client) -> list:
    """
    Retorna una lista de símbolos válidos para análisis con USDT como moneda base,
    excluyendo tokens apalancados, experimentales o de baja calidad.

    Args:
        client (binance.Client): Cliente autenticado de la API de Binance.

    Returns:
        list: Lista de símbolos (ej. ['BTCUSDT', 'ETHUSDT', ...])
    """
    pares_validos = []
    info = client.get_exchange_info()

    for s in info['symbols']:
        if (
            s['quoteAsset'] == 'USDT' and
            s['status'] == 'TRADING' and
            not any(excluido in s['symbol'] for excluido in EXCLUDED_TERMS)
        ):
            pares_validos.append(s['symbol'])

    return pares_validos
