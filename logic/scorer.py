from logic.indicators import is_bounce_confirmed, has_recent_ema_cross


def evaluar_tp_sl_ratio(tp, sl):
    try:
        ratio = abs(tp - sl) / abs(sl)
        return ratio >= 2.0  # Requiere al menos 2:1
    except ZeroDivisionError:
        return False


def calcular_score(tec):
    score = 0
    razones = []

    # === Validaciones generales ===
    vitalidad = tec.volumen_actual / tec.volumen_promedio if tec.volumen_promedio else 0
    atr_bajo = tec.atr < 0.3  # demasiado poco movimiento para una operación rentable
    if atr_bajo:
        return 0, ["ATR demasiado bajo"]

    if tec.tipo == 'LONG':
        if tec.rsi_1d < 30:
            score += 15
            razones.append("RSI 1D en sobreventa")
        if 40 <= tec.rsi_1d <= 55:
            score += 15
            razones.append("RSI 1D en acumulación")
        if tec.macd_1d > tec.macd_signal_1d:
            score += 15
            razones.append("MACD al alza")
        if tec.ema20 > tec.ema50 > tec.ema200:
            score += 20
            razones.append("EMAs en orden alcista")
        if is_bounce_confirmed(tec.symbol, direction='long'):
            score += 10
            razones.append("Rebote confirmado")
        if has_recent_ema_cross(tec.symbol, direction='long'):
            score += 10
            razones.append("Cruce reciente de EMAs")
    else:  # SHORT
        if tec.rsi_1d > 70:
            score += 15
            razones.append("RSI 1D en sobrecompra")
        if tec.rsi_1w > 60:
            score += 10
            razones.append("RSI 1W sobrecomprado")
        if tec.macd_1d < tec.macd_signal_1d:
            score += 15
            razones.append("MACD a la baja")
        if tec.ema20 < tec.ema50 < tec.ema200:
            score += 20
            razones.append("EMAs en orden bajista")
        if is_bounce_confirmed(tec.symbol, direction='short'):
            score += 10
            razones.append("Rebote confirmado hacia abajo")
        if has_recent_ema_cross(tec.symbol, direction='short'):
            score += 10
            razones.append("Cruce reciente de EMAs bajista")

    if vitalidad > 1.2:
        score += 10
        razones.append("Volumen actual alto")
    elif vitalidad < 0.7:
        score -= 10
        razones.append("Volumen bajo")

    if 0.5 <= tec.atr <= 5:
        score += 5
        razones.append("ATR saludable")

    if evaluar_tp_sl_ratio(tec.tp, tec.sl):
        score += 10
        razones.append("Relación TP/SL favorable")

    if tec.grids >= 5:
        score += 5
        razones.append("Grids suficientes para estrategia")

    return score, razones
