# analyzer.py
# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Optional, Tuple, Any

import numpy as np
import pandas as pd
import ta

import config
from data import IndicadoresTecnicos
from logic.levels import compute_levels
from logic.scorer import calcular_score, inferir_bias
from utils.logger import get_audit_logger

# volumen 24h real (futuros)
try:
    from utils.data_loader import get_quote_volume_usdt  # -> float|None
except Exception:
    get_quote_volume_usdt = None  # type: ignore

audit_logger = get_audit_logger()


# ------------------------------- helpers -------------------------------

def _klines_to_df(klines) -> pd.DataFrame:
    """
    Convierte klines (Binance) a DataFrame con columnas: open, high, low, close, volume.
    Espera filas tipo: [openTime, open, high, low, close, volume, closeTime, ...]
    """
    if not klines:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(klines)
    df = df[[1, 2, 3, 4, 5]].astype(float)
    df.columns = ["open", "high", "low", "close", "volume"]
    return df


def _lv(levels: Any, key: str, alt: str | None = None) -> Optional[float]:
    """
    Lectura robusta de niveles, admitiendo dict u objeto.
    key: 'entry' | 'stop_loss' | 'stop_profit' | 'take_profit' | 'r_multiple'
    """
    if levels is None:
        return None
    # dict
    if isinstance(levels, dict):
        if key in levels and levels[key] is not None:
            try:
                return float(levels[key])
            except Exception:
                return None
        if alt and alt in levels and levels[alt] is not None:
            try:
                return float(levels[alt])
            except Exception:
                return None
        return None
    # objeto con atributos
    val = getattr(levels, key, None)
    if val is None and alt:
        val = getattr(levels, alt, None)
    try:
        return float(val) if val is not None else None
    except Exception:
        return None


def _relaxed_bias(ema20_d: float, ema50_d: float, ema20_w: float, ema50_w: float,
                  rsi_d: float | None, rsi_w: float | None) -> str:
    """
    Modo 'relaxed': acepta dirección si al menos un marco (D/W) es consistente
    y el otro no contradice claramente. Fallback a RSI si hace falta.
    """
    up_d = ema20_d > ema50_d
    up_w = ema20_w > ema50_w
    down_d = ema20_d < ema50_d
    down_w = ema20_w < ema50_w

    if up_d and not down_w:
        return "LONG"
    if down_d and not up_w:
        return "SHORT"

    # Fallback: RSI
    try:
        if rsi_d is not None and rsi_w is not None:
            if rsi_d >= 52 and rsi_w >= 50:
                return "LONG"
            if rsi_d <= 48 and rsi_w <= 50:
                return "SHORT"
    except Exception:
        pass
    return "NONE"


# ------------------------------- core -------------------------------

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

    # Volumen USDT 24h de Futures (si hay función disponible)
    vol_usdt_24h = None
    try:
        if get_quote_volume_usdt:
            vol_usdt_24h = get_quote_volume_usdt(symbol)
    except Exception:
        vol_usdt_24h = None

    # Fallback: volumen de la última vela * precio (proxy)
    vol_usdt_proxy = float(df_d["volume"].iloc[-1] * precio)
    vol_usdt = float(vol_usdt_24h) if vol_usdt_24h is not None else vol_usdt_proxy

    if vol_usdt < config.VOLUMEN_MINIMO_USDT:
        audit_logger.info(
            f"{symbol} descartado: volumen USDT bajo {vol_usdt:.2f} < {config.VOLUMEN_MINIMO_USDT}"
        )
        return None

    # Tendencia diaria simple (solo informativa)
    if ema20_d > ema50_d > ema200_d:
        tendencia_diaria = "Alcista"
    elif ema20_d < ema50_d < ema200_d:
        tendencia_diaria = "Bajista"
    else:
        tendencia_diaria = "Lateral"

    # Consolidación (rango comprimido 20D) – informativo
    rango_20 = df_d["high"].rolling(20).max().iloc[-1] - df_d["low"].rolling(20).min().iloc[-1]
    consolidacion = "Consolidando" if rango_20 / max(precio, 1e-12) < 0.05 else "Sin consolidar"

    # Volumen creciente 3 días – informativo
    volumen_creciente = (
        len(df_d["volume"]) >= 4
        and df_d["volume"].iloc[-1] > df_d["volume"].iloc[-2] > df_d["volume"].iloc[-3]
    )

    # ---- 4) Sesgo (bias)
    tec_tmp = {
        "ema_fast_h1": ema20_d, "ema_slow_h1": ema50_d,
        "ema_fast_h4": ema20_w, "ema_slow_h4": ema50_w,
        "rsi14_h1": rsi_1d, "rsi14_h4": rsi_1w,
        "atr_pct": (atr / precio) if precio > 0 else None,
        "volume_usdt_24h": vol_usdt,
        "close": precio,
    }
    bias = inferir_bias(tec_tmp)

    # Modo relajado (si inferir_bias no encontró dirección)
    if (bias == "NONE" or bias is None) and getattr(config, "BIAS_MODE", "").lower() == "relaxed":
        bias = _relaxed_bias(ema20_d, ema50_d, ema20_w, ema50_w, rsi_1d, rsi_1w)

    if bias == "NONE" or bias is None:
        audit_logger.info(f"{symbol} descartado: sin sesgo operativo claro.")
        return None

    # Filtro global BTC/ETH (opcional)
    if getattr(config, "USE_GLOBAL_TREND_FILTER", False):
        if (bias == "LONG" and not (btc_alcista and eth_alcista)) or \
           (bias == "SHORT" and (btc_alcista and eth_alcista)):
            audit_logger.info(
                f"{symbol} descartado: contradicción con BTC/ETH. Bias {bias}, BTC {btc_alcista}, ETH {eth_alcista}"
            )
            return None
    else:
        # Solo informa, no bloquea
        if (bias == "LONG" and not (btc_alcista and eth_alcista)) or \
           (bias == "SHORT" and (btc_alcista and eth_alcista)):
            audit_logger.info(
                f"{symbol} contradice BTC/ETH (no bloquea). Bias {bias}, BTC {btc_alcista}, ETH {eth_alcista}"
            )

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
        )
    except Exception as e:
        audit_logger.info(f"{symbol} descartado en compute_levels: {e}")
        return None

    entry = _lv(levels, "entry")
    sl    = _lv(levels, "stop_loss", "sl")
    # aceptar stop_profit o take_profit
    tp    = _lv(levels, "stop_profit", "take_profit")
    r_mult = _lv(levels, "r_multiple")

    if entry is None or sl is None or tp is None:
        audit_logger.info(f"{symbol} descartado: niveles incompletos (entry/sl/tp).")
        return None

    # ---- 6) Filtros de calidad (longevidad)
    # RR
    R = abs(entry - sl)
    rr = (abs(tp - entry) / R) if R > 0 else 0.0
    rr_min = getattr(config, "RR_MIN", None)
    if rr_min is not None and rr < rr_min:
        audit_logger.info(f"{symbol} descartado: RR {rr:.2f} < {rr_min}")
        return None

    # ATR% sano
    atr_pct = (atr / max(precio, 1e-12))
    atr_min = getattr(config, "ATR_PCT_MIN", None)
    atr_max = getattr(config, "ATR_PCT_MAX", None)
    if atr_min is not None and atr_pct < atr_min:
        audit_logger.info(f"{symbol} descartado: ATR% {atr_pct:.4f} < {atr_min}")
        return None
    if atr_max is not None and atr_pct > atr_max:
        audit_logger.info(f"{symbol} descartado: ATR% {atr_pct:.4f} > {atr_max}")
        return None

    # ADX mínimo
    adx_min = getattr(config, "ADX_MIN", None)
    if adx_min is not None and adx < adx_min:
        audit_logger.info(f"{symbol} descartado: ADX {adx:.1f} < {adx_min}")
        return None

    # ---- 7) Armar objeto técnico (mantengo tu estructura + nuevos campos)
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
    # Añadir campos modernos si existen en la dataclass
    try:
        tec.entry = entry
        tec.stop_loss = sl
        tec.take_profit = tp
        tec.rr = rr
        tec.atr_pct = atr_pct
    except Exception:
        pass

    logging.debug(f"{symbol} valores: entry={entry}, sl={sl}, tp={tp}, atr={atr}, rr={rr:.2f}, atr%={atr_pct:.4f}")

    # ---- 8) Score (0..100) con desglose
    try:
        score, factors = calcular_score(tec, bias=bias)  # si tu calcular_score no acepta bias, quítalo
    except TypeError:
        score, factors = calcular_score(tec)  # compat
    logging.debug(f"{symbol} score: {score} | factores: {factors}")

    # Log síntesis
    log_info = (
        f"Análisis {symbol}:"
        f"\n- Tendencia diaria: {tendencia_diaria}"
        f"\n- {consolidacion}"
        f"\n- ADX: {adx:.2f}"
        f"\n- Volumen 24h (USDT): {vol_usdt:,.0f}"
        f"\n- Volumen creciente 3d: {'Sí' if volumen_creciente else 'No'}"
        f"\n[SCORE] Total: {score}/100 | Bias: {bias}"
        f"\nNiveles → Entry: {entry} | SL: {sl} | SP: {tp} (RR≈{rr:.2f}R)"
        f"\nATR%≈{atr_pct:.4f}"
    )
    logging.info(log_info)

    # Guardar desglose en el objeto (si tu clase lo soporta)
    try:
        tec.trend_score = float(factors.get("trend", 0.0))
        tec.volume_score = float(factors.get("volume", 0.0))
        tec.momentum_score = float(factors.get("momentum", 0.0))
        tec.volatility_score = float(factors.get("volatility", 0.0))
        tec.rr_score = float(factors.get("risk_reward", 0.0))
        tec.score = float(score)
    except Exception:
        pass

    # ---- 9) Umbral final de alerta
    if score >= config.MIN_SCORE_ALERTA:
        audit_logger.info("[DECISIÓN] Activo candidato.")
        return tec, score, factors, None
    else:
        motivo = f"Score {score} < {config.MIN_SCORE_ALERTA}"
        audit_logger.info(f"[DECISIÓN] {symbol} descartado: {motivo}")
        return None
