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
    precio = indicadores.get('precio')
    tp = indicadores.get('tp')
    sl = indicadores.get('sl')

    if precio is None or tp is None or sl is None:
        return False, 'Faltan niveles de precio'

    riesgo = abs(precio - sl)
    recompensa = abs(tp - precio)
    if riesgo == 0 or recompensa / riesgo < 2:
        return False, 'Relación TP/SL desfavorable'

    grids = round(np.log(abs(tp / precio)) / np.log(1 + GRIDS_GAP_PCT)) if tp != precio else 0
    if grids < 2:
        return False, 'TP demasiado cercano'

    # 4. Filtro global (BTC y ETH)
    if tipo == 'LONG' and not (btc_alcista and eth_alcista):
        return False, 'Mercado global bajista'
    if tipo == 'SHORT' and btc_alcista and eth_alcista:
        return False, 'Mercado global alcista'

    # 5. Filtro de volumen bajo o manipulado
    volumen_actual = indicadores.get('volumen_actual')
    volumen_promedio = indicadores.get('volumen_promedio', 0)
    if volumen_actual is not None:
        if volumen_actual * precio < VOLUMEN_MINIMO_USDT:
            return False, 'Volumen insuficiente'
        if volumen_promedio and volumen_actual < 0.5 * volumen_promedio:
            return False, 'Volumen decreciente'

    return True, 'OK'