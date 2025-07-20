# indicators.py
import pandas as pd
import numpy as np
import ta

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

    Esta implementación simple retorna ``False`` si no se dispone de datos
    históricos. Se considera un rebote confirmado cuando el precio atraviesa la
    EMA 200 y cierra nuevamente a favor de la dirección indicada.

    Parameters
    ----------
    symbol : str
        Símbolo de la criptomoneda (por ejemplo ``"BTCUSDT"``).
    direction : str
        ``"long"`` para rebotes alcistas, ``"short"`` para bajistas.
    lookback : int
        Número de velas a verificar.
    """
    # Placeholder: lógica de análisis pendiente de implementación completa.
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
    # Placeholder: se necesitarían datos históricos para un cálculo real.
    return False