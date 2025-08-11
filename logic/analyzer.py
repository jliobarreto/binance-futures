# analyzer.py
# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Optional, Tuple, Dict, Any
from types import SimpleNamespace
from math import isfinite

import numpy as np
import pandas as pd
import ta

import config
from logic.levels import compute_levels
from logic.scorer import inferir_bias  # mantenemos sólo el sesgo
from utils.logger import get_audit_logger

audit_logger = get_audit_logger()

# Parámetros base
ATR_PERIOD = 14
BB_PERIOD = 20
RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50
EMA_LONG = 200

# Umbrales/filtros (puedes sobreescribirlos en config)
ADX_MIN = getattr(config, "ADX_MIN", 12.0)          # filtro suave; si no lo quieres, pon 0 en config
MAX_ATR_PCT = getattr(config, "MAX_ATR_PCT", None)  # e.g. 0.10 para 10%


# ------------------------ utilidades internas ------------------------ #

def _klines_to_df(klines) -> pd.DataFrame:
    """
    Convierte klines a DataFrame [open, high, low, close, volume] (floats).
    Acepta lista de listas como entrega Binance ([ot, o, h, l, c, v, ...]) o DataFrame con headers.
    """
    if klines is None or len(klines) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(klines)
    try:
        df = df[[1, 2, 3, 4, 5]].astype(float)
    except Exception:
        cols = {str(c).lower(): c for c in df.columns}
        try:
            df = df[[cols["open"], cols["high"], cols["low"], cols["close"], cols["volume"]]].astype(float)
            df.columns = ["open", "high", "low", "close", "volume"]
            return df
        except Exception:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df.columns = ["open", "high", "low", "close", "volume"]
    return df


def _check_min_bars(df_d: pd.DataFrame, df_w: pd.DataFrame) -> Optional[str]:
    """
    Evita errores de series cortas antes de calcular indicadores.
    - Diario: al menos max(60, 3*ATR_PERIOD, 3*SWING_LOOKBACK)
    - Semanal: 10–14 velas
    """
    swing_lb = getattr(config, "SWING_LOOKBACK", 14)
    need_d = max(60, 3 * ATR_PERIOD, 3 * swing_lb)
    need_w = max(10, min(14, ATR_PERIOD))
    if len(df_d) < need_d or len(df_w) < need_w:
        return f"ShortSeries:D{len(df_d)}/W{len(df_w)} (need≈D{need_d}/W{need_w})"
    return None


def _estimate_vol_usdt(df: pd.DataFrame) -> float:
    """ Estima volumen USDT del último día como typical_price * volume. """
    if df.empty:
        return 0.0
    last = df.iloc[-1]
    tp = (last["high"] + last["low"] + last["close"]) / 3.0
    return float(tp * last["volume"])


def _sanitize_levels(
    bias: str,
    entry: float,
    sl: float,
    tp: float,
    df_d: pd.DataFrame,
    atr: float,
    tp_r_mult: float,
) -> Tuple[float, float, float, Dict[str, Any]]:
    """
    Sanea niveles absurdos y devuelve (entry, sl, tp, info_dict).
    - LONG: sl < entry < tp
    - SHORT: tp < entry < sl
    Apoya en swings y ATR si es necesario.
    """
    info = {}
    price_min_tick = 1e-12

    swing_lb = getattr(config, "SWING_LOOKBACK", 14)
    swing_high = float(df_d["high"].rolling(swing_lb).max().iloc[-1]) if len(df_d) >= swing_lb else float(df_d["high"].max())
    swing_low = float(df_d["low"].rolling(swing_lb).min().iloc[-1]) if len(df_d) >= swing_lb else float(df_d["low"].min())

    def _clamp_positive(x: float) -> float:
        return max(float(x), price_min_tick)

    if bias == "LONG":
        if sl >= entry:
            sl = _clamp_positive(min(entry - 1.5 * atr, (entry + swing_low) / 2.0))
            info["fix_sl_long"] = True
        if tp <= entry:
            rr_tp = entry + tp_r_mult * (entry - sl)
            tp = max(rr_tp, swing_high, entry + 1.5 * atr)
            info["fix_tp_long"] = True
    elif bias == "SHORT":
        if sl <= entry:
            sl = _clamp_positive(max(entry + 1.5 * atr, (entry + swing_high) / 2.0))
            info["fix_sl_short"] = True
        if tp >= entry or tp <= 0.0:
            rr_tp = entry - tp_r_mult * (sl - entry)
            tp = _clamp_positive(min(rr_tp, entry - 1.5 * atr, swing_low))
            info["fix_tp_short"] = True

    entry = float(entry)
    sl = _clamp_positive(sl)
    tp = _clamp_positive(tp)

    if bias == "LONG" and not (sl < entry < tp):
        sl = _clamp_positive(entry - 1.5 * atr)
        tp = _clamp_positive(entry + tp_r_mult * (entry - sl))
        info["force_long_levels"] = True

    if bias == "SHORT" and not (tp < entry < sl):
        sl = _clamp_positive(entry + 1.5 * atr)
        tp = _clamp_positive(entry - tp_r_mult * (sl - entry))
        info["force_short_levels"] = True

    return entry, sl, tp, info


def _build_tecnico_container(**fields: Any) -> Any:
    """
    Parche tolerante:
    - Intenta usar data.IndicadoresTecnicos como contenedor de atributos.
    - Si la firma no acepta ciertos kwargs, los filtra.
    - Si falla, usa SimpleNamespace con los mismos campos.
    """
    try:
        from data import IndicadoresTecnicos as Container  # contenedor ligero (no el de utils/indicators)
    except Exception:
        Container = None

    if Container is not None:
        try:
            import inspect
            sig = inspect.signature(Container.__init__)
            params = sig.parameters
            accepts_var_kw = any(p.kind == p.VAR_KEYWORD for p in params.values())
            if accepts_var_kw:
                return Container(**fields)
            allowed = {n for n in params.keys() if n != "self"}
            filtered = {k: v for k, v in fields.items() if k in allowed}
            return Container(**filtered)
        except TypeError:
            # reintento minimalista sin kwargs extraños
            try:
                return Container()
            except Exception:
                pass
        except Exception:
            pass

    # Fallback robusto
    ns = SimpleNamespace(**fields)
    return ns


# ------------------------ Scorer v2 (parche integrado) ------------------------ #

def _calc_rr(entry: float, sl: float, sp: float, side: str) -> float:
    """Calcula reward/risk en función del lado de la operación."""
    try:
        if any(x is None for x in (entry, sl, sp)) or entry <= 0:
            return 0.0
        side = (side or "LONG").upper()
        if side == "LONG":
            risk = max(entry - sl, 1e-12)
            reward = max(sp - entry, 0.0)
        else:
            risk = max(sl - entry, 1e-12)
            reward = max(entry - sp, 0.0)
        rr = reward / risk
        return rr if isfinite(rr) and rr > 0 else 0.0
    except Exception:
        return 0.0


def _score_signal_v2(feat: dict, cfg) -> tuple[float, Dict[str, float], str]:
    """
    Scorer v2 enfocado en calidad:
    - Pondera tendencia+ADX, R:R y liquidez
    - Penaliza volatilidad (ATR%) cerca del límite
    - Bonus leve si volumen ↑ 3d; penalización si consolidando
    Devuelve (score 0..100, factores_por_bloque, etiqueta)
    """
    side = str(feat.get("bias", "LONG")).upper()
    rr   = _calc_rr(feat.get("entry"), feat.get("sl"), feat.get("sp"), side)

    adx         = float(feat.get("adx", 0.0) or 0.0)
    atr_pct     = float(feat.get("atr_pct", 0.0) or 0.0)
    vol_usdt    = float(feat.get("vol_usdt_24h", feat.get("volume_usdt_24h", 0.0)) or 0.0)
    vol3_up     = bool(feat.get("vol_3d_up", False))
    tendencia   = feat.get("trend", "Lateral")  # 'Alcista' | 'Bajista' | 'Lateral'
    consolidando = bool(feat.get("consolidando", False))
    regime_align = bool(feat.get("regime_align", True))

    # Ponderaciones
    factors: Dict[str, float] = dict(trend=0.0, risk_reward=0.0, volatility=0.0, volume=0.0, momentum=0.0)

    # (1) Alineación con BTC/ETH (momentum)
    factors["momentum"] += (10.0 if regime_align else -8.0)

    # (2) Tendencia base + ADX
    if tendencia in ("Alcista", "Bajista"):
        factors["trend"] += 20.0
    elif tendencia == "Lateral":
        factors["trend"] += 8.0

    adx_norm = max(0.0, min(1.0, (adx - 12.0) / (32.0 - 12.0)))  # 12→0, 32→1
    factors["trend"] += 15.0 * adx_norm

    # (3) R:R (cap a 3R)
    rr_c = max(0.0, min(rr, 3.0))
    factors["risk_reward"] += (rr_c / 3.0) * 18.0

    # (4) Volatilidad (penalización)
    atr_cap = float(getattr(cfg, "MAX_ATR_PCT", 0.10) or 0.10)
    if atr_cap > 0:
        atr_ratio = min(1.0, atr_pct / atr_cap)  # 0..1
        factors["volatility"] += -10.0 * (atr_ratio ** 1.5)

    # (5) Liquidez
    vmin = float(getattr(cfg, "VOLUMEN_MINIMO_USDT", 25_000_000) or 25_000_000)
    if vol_usdt > 0 and vmin > 0:
        v_ratio = max(0.0, min(2.0, vol_usdt / vmin))  # cap 2x
        factors["volume"] += 12.0 * (v_ratio / 2.0)

    # (6) Volumen creciente 3d (+3)
    if vol3_up:
        factors["volume"] += 3.0

    # (7) Consolidación (-6) lo tratamos como "momentum"
    if consolidando:
        factors["momentum"] += -6.0

    # Suma y clamp
    score = sum(factors.values())
    score = max(0.0, min(100.0, score))
    tag = f"{score:.4f}/100 | Bias: {side}"
    return score, factors, tag


# ------------------------ analizador principal ------------------------ #

def analizar_simbolo(
    symbol: str,
    klines_d,  # velas diarias (lista de listas o DF)
    klines_w,  # velas semanales (lista de listas o DF)
    btc_alcista: bool,
    eth_alcista: bool,
) -> Optional[Tuple[Any, float, dict, None]]:
    # 1) Dataframes + mínimos
    df_d = _klines_to_df(klines_d)
    df_w = _klines_to_df(klines_w)
    if df_d.empty or df_w.empty:
        audit_logger.info(f"{symbol} descartado: df vacío (D/W).")
        return None

    short_reason = _check_min_bars(df_d, df_w)
    if short_reason:
        audit_logger.info(f"{symbol} descartado: {short_reason}.")
        return None

    close_d = df_d["close"]
    close_w = df_w["close"]

    # 2) Indicadores base
    try:
        rsi_1d = ta.momentum.RSIIndicator(close_d, RSI_PERIOD).rsi().iloc[-1]
        rsi_1w = ta.momentum.RSIIndicator(close_w, RSI_PERIOD).rsi().iloc[-1]

        macd_obj = ta.trend.MACD(close_d)
        macd_1d = macd_obj.macd().iloc[-1]
        macd_signal_1d = macd_obj.macd_signal().iloc[-1]

        ema20_d = ta.trend.EMAIndicator(close_d, EMA_FAST).ema_indicator().iloc[-1]
        ema50_d = ta.trend.EMAIndicator(close_d, EMA_SLOW).ema_indicator().iloc[-1]
        ema200_d = ta.trend.EMAIndicator(close_d, EMA_LONG).ema_indicator().iloc[-1]

        ema20_w = ta.trend.EMAIndicator(close_w, EMA_FAST).ema_indicator().iloc[-1]
        ema50_w = ta.trend.EMAIndicator(close_w, EMA_SLOW).ema_indicator().iloc[-1]

        atr_series = ta.volatility.AverageTrueRange(
            df_d["high"], df_d["low"], close_d, ATR_PERIOD
        ).average_true_range()
        atr = float(atr_series.iloc[-1])

        mfi = ta.volume.MFIIndicator(
            df_d["high"], df_d["low"], close_d, df_d["volume"], RSI_PERIOD
        ).money_flow_index().iloc[-1]
        obv = ta.volume.OnBalanceVolumeIndicator(
            close_d, df_d["volume"]
        ).on_balance_volume().iloc[-1]
        adx = ta.trend.ADXIndicator(
            df_d["high"], df_d["low"], close_d, RSI_PERIOD
        ).adx().iloc[-1]
        bb = ta.volatility.BollingerBands(close_d, window=BB_PERIOD, window_dev=2.0)
        boll_upper = bb.bollinger_hband().iloc[-1]
        boll_lower = bb.bollinger_lband().iloc[-1]
    except Exception as e:
        audit_logger.info(f"{symbol} descartado: error indicadores ({e}).")
        return None

    # 3) Filtros rápidos
    precio = float(close_d.iloc[-1])
    if precio <= 0 or not np.isfinite(precio):
        audit_logger.info(f"{symbol} descartado: precio inválido.")
        return None

    vol_usdt_est = _estimate_vol_usdt(df_d)
    vol_min = float(getattr(config, "VOLUMEN_MINIMO_USDT", 0))
    if vol_usdt_est < vol_min:
        audit_logger.info(f"{symbol} descartado: volumen USDT bajo {vol_usdt_est:.2f} < {vol_min}")
        return None

    if ADX_MIN and float(adx) < float(ADX_MIN):
        audit_logger.info(f"{symbol} descartado: ADX {adx:.2f} < {ADX_MIN}.")
        return None

    # Tendencia diaria simple
    if ema20_d > ema50_d > ema200_d:
        tendencia_diaria = "Alcista"
    elif ema20_d < ema50_d < ema200_d:
        tendencia_diaria = "Bajista"
    else:
        tendencia_diaria = "Lateral"

    # Consolidación (rango 20D)
    try:
        hh = df_d["high"].rolling(20).max().iloc[-1]
        ll = df_d["low"].rolling(20).min().iloc[-1]
        rango_20 = float(hh - ll)
    except Exception:
        rango_20 = float("inf")
    consolidacion = "Consolidando" if (precio > 0 and np.isfinite(rango_20) and (rango_20 / precio) < 0.05) else "Sin consolidar"

    # Volumen creciente 3 días
    volumen_creciente = (
        len(df_d["volume"]) >= 4
        and df_d["volume"].iloc[-1] > df_d["volume"].iloc[-2] > df_d["volume"].iloc[-3]
    )

    # 4) Sesgo (bias) + coherencia BTC/ETH
    tec_tmp = {
        "ema_fast_h1": float(ema20_d),
        "ema_slow_h1": float(ema50_d),
        "ema_fast_h4": float(ema20_w),
        "ema_slow_h4": float(ema50_w),
        "rsi14_h1": float(rsi_1d),
        "rsi14_h4": float(rsi_1w),
        "atr_pct": (atr / precio) if precio > 0 else None,
        "volume_usdt_24h": vol_usdt_est,
        "close": precio,
    }
    bias = inferir_bias(tec_tmp)
    if bias == "NONE":
        audit_logger.info(f"{symbol} descartado: sin sesgo operativo claro.")
        return None

    use_global = bool(getattr(config, "USE_GLOBAL_TREND_FILTER", False))
    bias_mode = str(getattr(config, "BIAS_MODE", "relaxed")).lower()
    contradiction = False
    if use_global:
        contradiction = (
            (bias == "LONG" and (not btc_alcista and not eth_alcista)) or
            (bias == "SHORT" and (btc_alcista and eth_alcista))
        )
        if contradiction and bias_mode in ("strict", "strong", "hard"):
            audit_logger.info(
                f"{symbol} descartado por régimen global (modo {bias_mode}). Bias {bias}, BTC {btc_alcista}, ETH {eth_alcista}"
            )
            return None
        elif contradiction:
            audit_logger.info(
                f"{symbol} contradice BTC/ETH (no bloquea). Bias {bias}, BTC {btc_alcista}, ETH {eth_alcista}"
            )

    # 5) Filtro ATR%
    atr_pct = (atr / precio) if precio > 0 else None
    if MAX_ATR_PCT is not None and atr_pct is not None and atr_pct > float(MAX_ATR_PCT):
        audit_logger.info(f"{symbol} descartado: ATR% {atr_pct:.3f} > {float(MAX_ATR_PCT)}")
        return None

    # 6) Niveles (Entry/SL/TP)
    df_levels = df_d.copy()
    try:
        atr_series = atr_series.astype(float)
    except Exception:
        pass
    df_levels["ATR"] = atr_series
    try:
        levels = compute_levels(
            df=df_levels,
            bias=bias,
            atr_sl_mult=getattr(config, "ATR_SL_MULT", 1.8),
            tp_r_mult=getattr(config, "TP_R_MULT", 2.0),
            swing_lookback=getattr(config, "SWING_LOOKBACK", 14),
            tick_size=None,
            atr_period=ATR_PERIOD,
            max_atr_pct=getattr(config, "MAX_ATR_PCT", None),
        )
    except Exception as e:
        audit_logger.info(f"{symbol} descartado en compute_levels: {e}")
        return None

    try:
        entry = float(levels.entry)
        sl = float(levels.stop_loss)
        tp = float(levels.stop_profit)
        rr = float(getattr(levels, "rr", np.nan))
    except Exception as e:
        audit_logger.info(f"{symbol} descartado: niveles inválidos ({e}).")
        return None

    entry, sl, tp, fix_info = _sanitize_levels(
        bias=bias,
        entry=entry,
        sl=sl,
        tp=tp,
        df_d=df_d,
        atr=atr,
        tp_r_mult=float(getattr(config, "TP_R_MULT", 2.0)),
    )

    # 7) Contenedor técnico (parche tolerante)
    tec_fields = dict(
        symbol=symbol,
        precio=precio,
        rsi_1d=float(rsi_1d),
        rsi_1w=float(rsi_1w),
        macd_1d=float(macd_1d),
        macd_signal_1d=float(macd_signal_1d),
        ema20_d=float(ema20_d),
        ema50_d=float(ema50_d),
        ema200_d=float(ema200_d),
        volumen=float(df_d["volume"].iloc[-1]),
        volumen_prom_30=float(df_d["volume"].tail(30).mean()),
        atr=float(atr),
        tipo=bias,                     # compatibilidad
        stop_profit=float(tp),         # único TP
        stop_loss=float(sl),
        resistencia=np.nan,
        grids=0,
        mfi=float(mfi),
        obv=float(obv),
        adx=float(adx),
        boll_upper=float(boll_upper),
        boll_lower=float(boll_lower),
        # extras
        entry=entry,
        take_profit=tp,
        bias=bias,
        rr=rr,
        atr_pct=float(atr_pct) if atr_pct is not None else None,
        volume_usdt_24h=float(vol_usdt_est),
    )
    tec = _build_tecnico_container(**tec_fields)

    # 8) Score (Scorer v2)
    features_v2 = {
        "bias": bias,
        "entry": entry,
        "sl": sl,
        "sp": tp,
        "adx": float(adx),
        "atr_pct": float(atr_pct) if atr_pct is not None else 0.0,
        "vol_usdt_24h": float(vol_usdt_est),
        "vol_3d_up": bool(volumen_creciente),
        "trend": tendencia_diaria,
        "consolidando": (consolidacion == "Consolidando"),
        "regime_align": (not contradiction),
    }
    score, factors, _tag = _score_signal_v2(features_v2, config)

    # 9) Log de síntesis
    fix_notes = "; ".join(sorted(fix_info.keys())) if fix_info else ""
    log_info = (
        f"Análisis {symbol}:"
        f"\n- Tendencia diaria: {tendencia_diaria}"
        f"\n- {consolidacion}"
        f"\n- ADX: {adx:.2f}"
        f"\n- Volumen 24h (USDT): {vol_usdt_est:,.0f}"
        f"\n- Volumen creciente 3d: {'Sí' if volumen_creciente else 'No'}"
        f"\n[SCORE] Total: {score:.4f}/100 | Bias: {bias}"
        f"\nNiveles → Entry: {entry} | SL: {sl} | SP: {tp} (RR≈{rr if np.isfinite(rr) else '—'}R)"
        f"\nATR%≈{(atr_pct if atr_pct is not None else float('nan')):.4f}"
        + (f"\n[LEVELS_FIX] {fix_notes}" if fix_notes else "")
    )
    logging.info(log_info)

    # Añade desglose al contenedor (si existe)
    try:
        tec.trend_score = float(factors.get("trend", 0.0))
        tec.volume_score = float(factors.get("volume", 0.0))
        tec.momentum_score = float(factors.get("momentum", 0.0))
        tec.volatility_score = float(factors.get("volatility", 0.0))
        tec.rr_score = float(factors.get("risk_reward", 0.0))
        tec.score = float(score)
    except Exception:
        pass

    # --- Aliases mínimos para el sender (sin cambiar el resto del pipeline) ---
    try:
        # Lado en formato común
        side_from = getattr(tec, "bias", getattr(tec, "tipo", "LONG"))
        tec.side = "BUY" if str(side_from).upper() == "LONG" else "SELL"
        # Alias cortos
        tec.tp = float(getattr(tec, "take_profit", getattr(tec, "stop_profit")))
        tec.sl = float(getattr(tec, "stop_loss"))
        tec.entry_price = float(getattr(tec, "entry", getattr(tec, "precio", 0.0)))
        tec.score = float(getattr(tec, "score", 0.0))
        # Paquete listo para enviar
        tec.alert_payload = {
            "symbol": getattr(tec, "symbol"),
            "side": tec.side,
            "entry": tec.entry_price,
            "stop": tec.sl,
            "target": tec.tp,
            "score": float(getattr(tec, "score", 0.0)),
            "rr": float(getattr(tec, "rr", 0.0)),
            "adx": float(getattr(tec, "adx", 0.0)),
        }
    except Exception:
        pass
    # --- fin aliases ---

    # 10) Decisión por umbral
    min_score = float(getattr(config, "MIN_SCORE_ALERTA", 55))
    if score >= min_score:
        audit_logger.info("[DECISIÓN] Activo candidato.")
        return tec, score, factors, None
    else:
        motivo = f"Score {score:.2f} < {min_score:.2f}"
        audit_logger.info(f"[DECISIÓN] {symbol} descartado: {motivo}")
        return None
