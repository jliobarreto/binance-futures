# analyzer.py

import pandas as pd
import numpy as np
import ta
import logging
from logic.scorer import calcular_score
from logic.longterm import valida_entrada_largo_plazo
from data.models import IndicadoresTecnicos
from config import VOLUMEN_MINIMO_USDT, GRIDS_GAP_PCT, MIN_SCORE_ALERTA


def analizar_simbolo(symbol, klines_d, klines_w, btc_alcista, eth_alcista):
    df_d = pd.DataFrame(klines_d).astype(float)
    df_w = pd.DataFrame(klines_w).astype(float)
    close_d = df_d[4]
    close_w = df_w[4]

# Indicadores
    rsi_1d = ta.momentum.RSIIndicator(close_d, 14).rsi().iloc[-1]
    rsi_1w = ta.momentum.RSIIndicator(close_w, 14).rsi().iloc[-1]
    macd_obj = ta.trend.MACD(close_d)
    macd_1d = macd_obj.macd().iloc[-1]
    macd_signal_1d = macd_obj.macd_signal().iloc[-1]
    ema20 = ta.trend.EMAIndicator(close_d, 20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close_d, 50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close_d, 200).ema_indicator().iloc[-1]
    ema50_w = ta.trend.EMAIndicator(close_w, 50).ema_indicator().iloc[-1]
    ema200_w = ta.trend.EMAIndicator(close_w, 200).ema_indicator().iloc[-1]
    if ema50_w > ema200_w:
        tendencia_semanal = "Alcista"
    elif ema50_w < ema200_w:
        tendencia_semanal = "Bajista"
    else:
        tendencia_semanal = "Indefinida"
    atr = ta.volatility.AverageTrueRange(df_d[2], df_d[3], close_d, 14).average_true_range().iloc[-1]
    mfi = ta.volume.MFIIndicator(df_d[2], df_d[3], close_d, df_d[5], 14).money_flow_index().iloc[-1]
    obv = ta.volume.OnBalanceVolumeIndicator(close_d, df_d[5]).on_balance_volume().iloc[-1]
    adx = ta.trend.ADXIndicator(df_d[2], df_d[3], close_d, 14).adx().iloc[-1]
    boll_upper = ta.volatility.BollingerBands(close_d).bollinger_hband().iloc[-1]
    boll_lower = ta.volatility.BollingerBands(close_d).bollinger_lband().iloc[-1]

    logging.debug(
        f"{symbol} indicadores: RSI1D={rsi_1d:.2f}, RSI1W={rsi_1w:.2f}, "
        f"MACD1D={macd_1d:.4f}, MACD_signal1D={macd_signal_1d:.4f}, "
        f"EMA20={ema20:.4f}, EMA50={ema50:.4f}, EMA200={ema200:.4f}, "
        f"ATR={atr:.4f}, MFI={mfi:.2f}, OBV={obv:.2f}, ADX={adx:.2f}, "
        f"Boll_upper={boll_upper:.4f}, Boll_lower={boll_lower:.4f}"
    )

    es_valido, motivo_lp = valida_entrada_largo_plazo(df_d, df_w)
    if not es_valido:
        logging.debug(f"{symbol} descartado por validación de largo plazo: {motivo_lp}")
        return None

    precio = close_d.iloc[-1]
    volumen_actual = df_d[5].iloc[-1]
    volumen_promedio = df_d[5].tail(30).mean()

git add .           
git commit -m "V1.0.0.12"  
git push      logging.debug(
    def analizar_simbolo(symbol, klines_d, klines_w, btc_alcista, eth_alcista):
    # SL con ATR
    sl = precio - 1.5 * atr if tipo == 'LONG' else precio + 1.5 * atr

    # Resistencia o soporte
    resistencia = df_d[2].rolling(60).max().iloc[-1] if tipo == 'LONG' else df_d[3].rolling(60).min().iloc[-1]
    distancia_tp = abs(resistencia - precio)
    umbral_atr = 3 * atr
    tp = resistencia if distancia_tp >= umbral_atr else precio + 6 * atr if tipo == 'LONG' else precio - 6 * atr

    # Grids
    grids = round(np.log(abs(tp / precio)) / np.log(1 + GRIDS_GAP_PCT)) if tp != precio else 0

    tec = IndicadoresTecnicos(
        symbol, precio, rsi_1d, rsi_1w, macd_1d, macd_signal_1d,
        ema20, ema50, ema200,
        volumen_actual, volumen_promedio, atr, tipo, tp, sl, resistencia,
        grids, mfi, obv, adx, boll_upper, boll_lower
    )

    logging.debug(
        f"{symbol} valores calculados: precio={precio}, tp={tp}, sl={sl}, grids={grids}"
    )

    score, factors = calcular_score(tec)
    logging.debug(f"{symbol} score: {score} | factores: {factors}")

    log_info = [
        f"\n🪙 {symbol}",
        f"- Tipo: {tipo}",
        f"- Score: {score:.2f}",
        f"- Tendencia semanal: {tendencia_semanal}",
        f"- RSI diario/semanal: {rsi_1d:.2f}/{rsi_1w:.2f}",
    ]
    logging.info("\n".join(log_info))
    tec.trend_score = factors["trend"]
    tec.volume_score = factors["volume"]
    tec.momentum_score = factors["momentum"]
    tec.volatility_score = factors["volatility"]
    tec.rr_score = factors["risk_reward"]
    tec.score = score
    if score >= MIN_SCORE_ALERTA:
        return tec, score, factors
    logging.debug(
        f"{symbol} descartado por score insuficiente ({score} < {MIN_SCORE_ALERTA})"
    )
    return None
