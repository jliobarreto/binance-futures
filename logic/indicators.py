# indicators.py
import pandas as pd
import numpy as np
import ta
from binance.client import Client
from config import BINANCE_API_KEY, BINANCE_API_SECRET

def calcular_macd(close: pd.Series):
    macd_obj = ta.trend.MACD(close)
    return macd_obj.macd().iloc[-1], macd_obj.macd_signal().iloc[-1]


def calcular_ema(close: pd.Series, periodo: int) -> float:
    return ta.trend.EMAIndicator(close, window=periodo).ema_indicator().iloc[-1]


def calcular_atr(high: pd.Series, low: pd.Series, close: pd.Series, periodo: int = 14) -> float:
    return ta.volatility.AverageTrueRange(high, low, close, window=periodo).average_true_range().iloc[-1]


def calcular_adx(high: pd.Series, low: pd.Series, close: pd.Series, periodo: int = 14) -> float:
    return ta.trend.ADXIndicator(high, low, close, window=periodo).adx().iloc[-1]


def calcular_bollinger_bands(close: pd.Series, periodo: int = 20):
    bb = ta.volatility.BollingerBands(close, window=periodo, window_dev=2)
    return bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1], bb.bollinger_mavg().iloc[-1]


def calcular_mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, periodo: int = 14) -> float:
    return ta.volume.MFIIndicator(high, low, close, volume, window=periodo).money_flow_index().iloc[-1]


def is_bounce_confirmed(symbol: str, direction: str = "long", lookback: int = 5) -> bool:
    """Evalúa si hubo un rebote en la EMA 200 en las últimas velas.

    Un rebote se considera confirmado cuando el precio cierra de un lado de la
    EMA200 después de haber cerrado en el lado opuesto en la vela previa. Para
    obtener los precios se consultan las velas diarias de Binance.

    Parameters
    ----------
    symbol : str
        Símbolo de la criptomoneda (por ejemplo ``"BTCUSDT"``).
    direction : str
        ``"long"`` para rebotes alcistas, ``"short"`` para bajistas.
    lookback : int
        Número de velas a verificar.
    """
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

    # Se solicitan suficientes velas para calcular la EMA200
    limit = max(lookback + 205, 210)
    klines = client.get_klines(
        symbol=symbol, interval=Client.KLINE_INTERVAL_1DAY, limit=limit
    )

    df = pd.DataFrame(klines).astype(float)
    close = df[4]

    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()

    for i in range(-lookback + 1, 0):
        prev_close = close.iloc[i - 1]
        curr_close = close.iloc[i]

        prev_above = prev_close > ema200.iloc[i - 1]
        curr_above = curr_close > ema200.iloc[i]

        if direction == "long" and not prev_above and curr_above:
            return True
        if direction == "short" and prev_above and not curr_above:
            return True

    return False


def has_recent_ema_cross(symbol: str, direction: str = "long", lookback: int = 10) -> bool:
    """Comprueba si hubo un cruce reciente de las EMAs 20 y 50.

    Devuelve ``True`` si en las últimas ``lookback`` velas la EMA20 cruzó la EMA50
    en la dirección indicada. La función está pensada como ayuda para filtrar
    entradas cuando recién cambia la tendencia.

    Parameters
    ----------
    symbol : str
        Par a consultar.
    direction : str
        ``"long"`` valida cruces alcistas, ``"short"`` cruces bajistas.
    lookback : int
        Cantidad de velas evaluadas.
    """
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

    limit = max(lookback + 55, 60)
    klines = client.get_klines(
        symbol=symbol, interval=Client.KLINE_INTERVAL_1DAY, limit=limit
    )

    close = pd.Series([float(k[4]) for k in klines])
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()

    diff = ema20 - ema50

    for i in range(-lookback + 1, 0):
        prev_diff = diff.iloc[i - 1]
        curr_diff = diff.iloc[i]

        if direction == "long" and prev_diff <= 0 and curr_diff > 0:
            return True
        if direction == "short" and prev_diff >= 0 and curr_diff < 0:
            return True

    return False