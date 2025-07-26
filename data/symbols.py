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

def obtener_top_usdt(client: Client, top_n: int = 30) -> list:
    """Devuelve los pares USDT con mayor volumen en 24h.

    Consulta las estadísticas de precio para obtener el ``quoteVolume`` de cada
    par y ordena de mayor a menor.

    Parameters
    ----------
    client: :class:`binance.client.Client`
        Cliente autenticado de la API.
    top_n: int, default ``30``
        Número de resultados a retornar.

    Returns
    -------
    list[str]
        Símbolos ordenados por volumen descendente.
    """

    try:
        tickers = client.get_ticker()
    except AttributeError:  # pragma: no cover - depende de la versión de la API
        tickers = client.get_ticker_price_change_stats()

    volumenes = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if symbol.endswith("USDT") and not any(ex in symbol for ex in EXCLUDED_TERMS):
            volumen = float(t.get("quoteVolume", 0))
            volumenes.append((symbol, volumen))

    volumenes.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in volumenes[:top_n]]
