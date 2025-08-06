import pandas as pd
import ta
from binance.client import Client
import config


def _es_alcista(client: Client, symbol: str) -> bool:
    """Evalúa si un símbolo está en tendencia alcista usando EMAs."""
    klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1DAY, limit=200)
    close = pd.Series([float(k[4]) for k in klines])
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1]
    return ema50 > ema200


def tendencia_mercado_global() -> tuple[bool, bool]:
    """Retorna la tendencia alcista de BTC y ETH en marco diario."""
    client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
    btc_alcista = _es_alcista(client, "BTCUSDT")
    eth_alcista = _es_alcista(client, "ETHUSDT")
    return btc_alcista, eth_alcista
