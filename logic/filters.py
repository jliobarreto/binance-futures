# filters.py
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
    