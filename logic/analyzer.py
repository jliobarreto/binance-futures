# analyzer.py
# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import ta

import config
from data import IndicadoresTecnicos
from logic.levels import compute_levels
from logic.scorer import calcular_score, inferir_bias
from utils.logger import get_audit_logger

audit_logger = get_audit_logger()


def _klines_to_df(klines) -> pd.DataFrame:
    """
    Convierte klines Binance a DataFrame con columnas nombradas.
    Espera filas tipo: [ot, open, high, low, close, volume, ...]
    """
    if klines is None or len(klines) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(klines)
    # Tomamos solo columnas esenciales
    df = df[[1, 2, 3, 4, 5]].astype(float)
    df.columns = ["open", "high", "low", "close", "volume"]
    return df


def analizar_simbolo(
    symbol: str,
    klines_d,  # velas diarias
    klines_w,  # velas semanales
    btc_alcista: bool,
    eth_alcista: bool,
) -> Optional[Tuple[IndicadoresTecnicos, float, dict, None]]:
    # ---- 1) Dataframes limpios
    df_d = _klines_to_df(klines_d)
    df_w = _klines_to_df(klines_w)
    if df_d.empty or df_w.empty:
        audit_logger.info(f"{symbol} descartado: df vacío (D/W).")
        return None

    close_d = df_d["close"]
    close_w = df_w["close"]

    # ---- 2) Indicadores base (D/W)
    rsi_1d = ta.momentum.RSIIndicator(close_d, 14).rsi().iloc[-1]
    rsi_1w = ta.momentum.RSIIndicator(close_w, 14).rsi().iloc[-1]

    macd_obj = ta.trend.MACD(close_d)
    macd_1d = macd_obj.macd().iloc[-1]
    macd_signal_1d = macd_obj.macd_signal().iloc[-1]

    ema20_d = ta.trend.EMAIndicator(close_d, 20).ema_indicator().iloc[-1]
    ema50_d = ta.trend.EMAIndicator(close_d, 50).ema_indicator().iloc[-1]
    ema200_d = ta.trend.EMAIndicator(close_d, 200).ema_indicator().iloc[-1]

    # EMAs en semanal para sesgo de marco mayor
    ema20_w = ta.trend.EMAIndicator(close_w, 20).ema_indicator().iloc[-1]
    ema50_w = ta.trend.EMAIndicator(close_w, 50).ema_indicator().iloc[-1]

    atr_series = ta.volatility.AverageTrueRange(
        df_d["high"], df_d["low"], close_d, 14
    ).average_true_range()
    atr = float(atr_series.iloc[-1])

    mfi = ta.volume.MFIIndicator(
        df_d["high"], df_d["low"], close_d, df_d["volume"], 14
    ).money_flow_index().iloc[-1]
    obv = ta.volume.OnBalanceVolumeIndicator(
        close_d, df_d["volume"]
    ).on_balance_volume().iloc[-1]
    adx = ta.trend.ADXIndicator(
        df_d["high"], df_d["low"], close_d, 14
    ).adx().iloc[-1]
    bb = ta.volatility.BollingerBands(close_d)
    boll_upper = bb.bollinger_hband().iloc[-1]
    boll_lower = bb.bollinger_lband().iloc[-1]

    # ---- 3) Filtros rápidos
    precio = float(close_d.iloc[-1])
    # Aproximación a volumen USDT (base_vol * precio). Mejoraremos con quoteVolume en otro módulo.
    vol_usdt_est = float(df_d["volume"].iloc[-1] * precio)
    if vol_usdt_est < config.VOLUMEN_MINIMO_USDT:
        audit_logger.info(
            f"{symbol} descartado: volumen USDT bajo {vol_usdt_est:.2f} < {config.VOLUMEN_MINIMO_USDT}"
        )
        return None

    # Tendencia diaria simple
    if ema20_d > ema50_d > ema200_d:
        tendencia_diaria = "Alcista"
    elif ema20_d < ema50_d < ema200_d:
        tendencia_diaria = "Bajista"
    else:
        tendencia_diaria = "Lateral"

    # Consolidación (rango comprimido 20D)
    rango_20 = df_d["high"].rolling(20).max().iloc[-1] - df_d["low"].rolling(20).min().iloc[-1]
    consolidacion = "Consolidando" if rango_20 / precio < 0.05 else "Sin consolidar"

    # Volumen creciente 3 días
    volumen_creciente = (
        len(df_d["volume"]) >= 4
        and df_d["volume"].iloc[-1] > df_d["volume"].iloc[-2] > df_d["volume"].iloc[-3]
    )

    # ---- 4) Sesgo (bias) y coherencia con BTC/ETH
    # Reutilizamos la función del scorer: mapeamos "H1/H4" a "D/W" para mantener compatibilidad.
    tec_tmp = {
        "ema_fast_h1": ema20_d, "ema_slow_h1": ema50_d,
        "ema_fast_h4": ema20_w, "ema_slow_h4": ema50_w,
        "rsi14_h1": rsi_1d, "rsi14_h4": rsi_1w,
        "atr_pct": (atr / precio) if precio > 0 else None,
        "volume_usdt_24h": vol_usdt_est,  # proxy
        "close": precio,
    }
    bias = inferir_bias(tec_tmp)
    if bias == "NONE":
        audit_logger.info(f"{symbol} descartado: sin sesgo operativo claro.")
        return None

    # coherencia simple de régimen con BTC/ETH
    if (bias == "LONG" and not (btc_alcista and eth_alcista)) or \
       (bias == "SHORT" and (btc_alcista and eth_alcista)):
        audit_logger.info(
            f"{symbol} descartado: contradicción con tendencia global. Bias {bias}, BTC {btc_alcista}, ETH {eth_alcista}"
        )
        return None

    # ---- 5) Niveles operativos: Entry / SL / StopProfit (único)
    df_levels = df_d.copy()
    df_levels["ATR"] = atr_series  # compute_levels usará esta serie si existe
    try:
        levels = compute_levels(
            df=df_levels,
            bias=bias,
            atr_sl_mult=getattr(config, "ATR_SL_MULT", 1.8),
            tp_r_mult=getattr(config, "TP_R_MULT", 2.0),
            swing_lookback=getattr(config, "SWING_LOOKBACK", 14),
            tick_size=None,  # TODO: integrar tickSize real de Futures
            atr_period=14,
            max_atr_pct=getattr(config, "MAX_ATR_PCT", None),  # p.ej. 0.12 para 12%
        )
    except Exception as e:
        audit_logger.info(f"{symbol} descartado en compute_levels: {e}")
        return None

    entry = float(levels.entry)
    sl = float(levels.stop_loss)
    tp = float(levels.stop_profit)

    # ---- 6) Armar objeto técnico (mantengo tu estructura + nuevos campos)
    tec = IndicadoresTecnicos(
        symbol,
        precio,
        rsi_1d,
        rsi_1w,
        macd_1d,
        macd_signal_1d,
        ema20_d,
        ema50_d,
        ema200_d,
        float(df_d["volume"].iloc[-1]),
        float(df_d["volume"].tail(30).mean()),
        atr,
        bias,         # reemplaza "tipo"
        tp,           # StopProfit (único)
        sl,           # StopLoss
        np.nan,       # resistencia/soporte (no lo usamos ahora)
        0,            # grids (fuera de alcance actual)
        mfi,
        obv,
        adx,
        boll_upper,
        boll_lower,
    )
    # Si tu dataclass no admite atributos extra, omite estas líneas:
    try:
        tec.entry = entry
        tec.take_profit = tp
        tec.stop_loss = sl
    except Exception:
        pass

    logging.debug(f"{symbol} valores: entry={entry}, sl={sl}, tp={tp}, atr={atr}")

    # ---- 7) Score (0..100) con desglose; usa sesgo calculado
    score, factors = calcular_score(tec, bias=bias)  # si tu calcular_score no acepta bias, quítalo
    logging.debug(f"{symbol} score: {score} | factores: {factors}")

    # Log síntesis
    log_info = (
        f"Análisis {symbol}:"
        f"\n- Tendencia diaria: {tendencia_diaria}"
        f"\n- {consolidacion}"
        f"\n- ADX: {adx:.2f}"
        f"\n- Volumen creciente 3d: {'Sí' if volumen_creciente else 'No'}"
        f"\n[SCORE] Total: {score}/100 | Bias: {bias}"
        f"\nNiveles → Entry: {entry} | SL: {sl} | SP: {tp} (RR≈{getattr(levels, 'rr', np.nan)}R)"
    )
    logging.info(log_info)

    # Guardar desglose en el objeto (si tu clase lo soporta)
    try:
        tec.trend_score = factors.get("trend", 0.0)
        tec.volume_score = factors.get("volume", 0.0)
        tec.momentum_score = factors.get("momentum", 0.0)
        tec.volatility_score = factors.get("volatility", 0.0)
        tec.rr_score = factors.get("risk_reward", 0.0)
        tec.score = score
    except Exception:
        pass

    if score >= config.MIN_SCORE_ALERTA:
        audit_logger.info("[DECISIÓN] Activo candidato.")
        return tec, score, factors, None
    else:
        motivo = f"Score {score} < {config.MIN_SCORE_ALERTA}"
        audit_logger.info(f"[DECISIÓN] {symbol} descartado: {motivo}")
        return None
