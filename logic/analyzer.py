# -*- coding: utf-8 -*-
# analyzer.py

import pandas as pd
import numpy as np
import ta
import logging
from logic.scorer import calcular_score
from logic.longterm import valida_entrada_largo_plazo
from data import IndicadoresTecnicos
import config
from utils.logger import get_audit_logger

audit_logger = get_audit_logger()

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
    atr = ta.volatility.AverageTrueRange(df_d[2], df_d[3], close_d, 14).average_true_range().iloc[-1]
    mfi = ta.volume.MFIIndicator(df_d[2], df_d[3], close_d, df_d[5], 14).money_flow_index().iloc[-1]
    obv = ta.volume.OnBalanceVolumeIndicator(close_d, df_d[5]).on_balance_volume().iloc[-1]
    adx = ta.trend.ADXIndicator(df_d[2], df_d[3], close_d, 14).adx().iloc[-1]
    boll_upper = ta.volatility.BollingerBands(close_d).bollinger_hband().iloc[-1]
    boll_lower = ta.volatility.BollingerBands(close_d).bollinger_lband().iloc[-1]

    # Tendencia diaria simple basada en EMAs
    if ema20 > ema50 > ema200:
        tendencia_diaria = "Alcista"
    elif ema20 < ema50 < ema200:
        tendencia_diaria = "Bajista"
    else:
        tendencia_diaria = "Lateral"

    # Consolidación mediante rango de las últimas 20 velas
    rango_20 = df_d[2].rolling(20).max().iloc[-1] - df_d[3].rolling(20).min().iloc[-1]
    consolidacion = "Consolidando" if rango_20 / close_d.iloc[-1] < 0.05 else "Sin consolidar"

    # Valida si el volumen ha aumentado durante los últimos tres días
    volumen_creciente = (
        len(df_d[5]) >= 4
        and df_d[5].iloc[-1] > df_d[5].iloc[-2] > df_d[5].iloc[-3]
    )

    es_valido, motivo_lp = valida_entrada_largo_plazo(df_d, df_w)
    if not es_valido:
        motivo = f"Validación largo plazo: {motivo_lp}"
        audit_logger.info(f"{symbol} descartado por {motivo}")
        return None

    precio = close_d.iloc[-1]
    volumen_actual = df_d[5].iloc[-1]
    volumen_promedio = df_d[5].tail(30).mean()

    logging.debug(
        f"Analizando {symbol} | Volumen actual: {volumen_actual} | Volumen promedio: {volumen_promedio}"
    )

    if volumen_actual * precio < config.VOLUMEN_MINIMO_USDT:
        motivo = (
            f"Volumen bajo: {volumen_actual * precio} < {config.VOLUMEN_MINIMO_USDT}"
        )
        audit_logger.info(f"{symbol} descartado por {motivo}")
        return None

    tipo = "LONG"
    if (
        rsi_1d > config.RSI_OVERBOUGHT
        and rsi_1w > config.RSI_WEEKLY_OVERBOUGHT
        and macd_1d < macd_signal_1d
        and ema20 < ema50 < ema200
    ):
        tipo = "SHORT"

    if (tipo == "LONG" and not (btc_alcista and eth_alcista)) or (
        tipo == "SHORT" and btc_alcista and eth_alcista
    ):
        motivo = (
            f"Contradicción con tendencia global. Tipo {tipo}, BTC {btc_alcista}, ETH {eth_alcista}"
        )
        audit_logger.info(f"{symbol} descartado por {motivo}")
        return None

    # SL con ATR
    sl = precio - 1.5 * atr if tipo == 'LONG' else precio + 1.5 * atr

    # Resistencia o soporte
    resistencia = df_d[2].rolling(60).max().iloc[-1] if tipo == 'LONG' else df_d[3].rolling(60).min().iloc[-1]
    distancia_tp = abs(resistencia - precio)
    umbral_atr = 3 * atr
    tp = resistencia if distancia_tp >= umbral_atr else precio + 6 * atr if tipo == 'LONG' else precio - 6 * atr

    # Grids
    grids = round(np.log(abs(tp / precio)) / np.log(1 + config.GRIDS_GAP_PCT)) if tp != precio else 0

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
    log_info = (
        f"Análisis de {symbol}:"
        f"\n- Tendencia diaria: {tendencia_diaria}"
        f"\n- {consolidacion}"
        f"\n- ADX: {adx:.2f}"
        f"\n- Volumen creciente 3 días: {'Sí' if volumen_creciente else 'No'}"
        f"\n[SCORE] Total: {score}/100"
    )
    logging.info(log_info)
    tec.trend_score = factors["trend"]
    tec.volume_score = factors["volume"]
    tec.momentum_score = factors["momentum"]
    tec.volatility_score = factors["volatility"]
    tec.rr_score = factors["risk_reward"]
    tec.score = score
    if score >= config.MIN_SCORE_ALERTA:
        audit_logger.info("[DECISIÓN] Activo candidato – pendiente validación BTC")
        return tec, score, factors, None
    else:
        motivo = f"Score {score} < {config.MIN_SCORE_ALERTA}"
        audit_logger.info(
            f"[DECISIÓN] {symbol} descartado por score insuficiente ({motivo})"
        )
        return None
