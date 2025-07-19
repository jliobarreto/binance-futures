# filters.py
from logic.indicators import get_indicators
from config import GRIDS_GAP_PCT, VOLUMEN_MINIMO_USDT
import numpy as np

# Mejora 1: Confirmación con temporalidades mayores
# Mejora 2: Consolidación previa + ruptura
# Mejora 3: Validación estructural del SL y TP
# Mejora 4: Filtro global (BTC y ETH)
# Mejora 5: Filtro de volumen bajo o manipulado

def cumple_mejoras_tecnicas(datos_1d, datos_1w, indicadores, tipo, btc_alcista, eth_alcista):
    # 1. Confirmación multi-timeframe
    if tipo == 'LONG' and indicadores['rsi_1w'] > 70:
        return False, 'RSI semanal sobrecomprado'
    if tipo == 'SHORT' and indicadores['rsi_1w'] < 30:
        return False, 'RSI semanal sobrevendido'

    # 2. Consolidación previa + ruptura
    velas = datos_1d['close'].tail(10).values
    rango = max(velas) - min(velas)
    ruptura = abs(velas[-1] - velas[-2]) > 0.75 * rango
    if rango < 0.05 * datos_1d['close'].iloc[-1] or not ruptura:
        return False, 'No hay ruptura tras consolidación'

    # 3. Validación estructural del SL y TP
    precio = indicadores['precio']
    atr = indicadores['atr']
    if tipo == 'LONG':
        sl = precio - 1.5 * atr
        tp = precio + 3 * atr
    else:
        sl = precio + 1.5 * atr
        tp = precio - 3 * atr
    if abs(tp - precio) < 2 * atr:
        return False, 'TP muy cercano (menos de 2 ATR)'

    # 4. Filtro de mercado global (BTC y ETH)
    if tipo == 'LONG' and not (btc_alcista and eth_alcista):
        return False, 'Mercado global no favorable para LONG'
    if tipo == 'SHORT' and btc_alcista and eth_alcista:
        return False, 'Mercado global no favorable para SHORT'

    # 5. Filtro de volumen bajo o manipulado
    volumen = indicadores['volumen']
    promedio = indicadores['volumen_promedio']
    vitalidad = volumen / promedio if promedio else 0
    if volumen * precio < VOLUMEN_MINIMO_USDT:
        return False, 'Volumen demasiado bajo'
    if vitalidad < 0.5 or vitalidad > 5:
        return False, 'Vitalidad anormal (manipulación posible)'

    return True, 'Pasa todos los filtros'

def calcular_sl_tp(precio, atr, tipo):
    if tipo == 'LONG':
        return precio - 1.5 * atr, precio + 3 * atr
    else:
        return precio + 1.5 * atr, precio - 3 * atr

def calcular_grids(precio, tp):
    if tp == precio:
        return 0
    return round(np.log(abs(tp / precio)) / np.log(1 + GRIDS_GAP_PCT))