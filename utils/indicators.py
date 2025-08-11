# utils/indicators.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


def _col(df: pd.DataFrame, name: str, cols: Dict[str, str]) -> pd.Series:
    """Devuelve una columna mapeada (con fallback en minúsculas)."""
    if name in cols:
        key = cols[name]
        if key in df.columns:
            return df[key]
    # Fallback por nombre común
    candidates = [
        name,
        name.capitalize(),
        name.upper(),
        name.lower(),
    ]
    for c in candidates:
        if c in df.columns:
            return df[c]
    raise KeyError(f"No se encontró columna '{name}' en {list(df.columns)}")


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False, min_periods=span).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down.replace(0.0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _atr(df: pd.DataFrame, period: int = 14, cols: Dict[str, str] = None) -> pd.Series:
    high = _col(df, "high", cols)
    low = _col(df, "low", cols)
    close = _col(df, "close", cols)
    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    return atr


def _adx(df: pd.DataFrame, period: int = 14, cols: Dict[str, str] = None) -> pd.Series:
    # Implementación clásica de Wilder
    high = _col(df, "high", cols).astype(float)
    low = _col(df, "low", cols).astype(float)
    close = _col(df, "close", cols).astype(float)

    plus_dm = (high.diff()).clip(lower=0.0)
    minus_dm = (-low.diff()).clip(lower=0.0)

    plus_dm[plus_dm < minus_dm] = 0.0
    minus_dm[minus_dm <= plus_dm] = 0.0

    tr = _atr(df, 1, cols)  # True Range diario (sin suavizar)
    tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()

    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / tr_smooth.replace(0.0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / tr_smooth.replace(0.0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    return adx


def _last(series: pd.Series) -> float:
    try:
        return float(series.dropna().iloc[-1])
    except Exception:
        return float("nan")


def _infer_quote_volume(df: pd.DataFrame) -> Optional[pd.Series]:
    # Intenta encontrar volumen en USDT (quote)
    candidates = [
        "quote_volume", "quoteVolume",
        "quote_asset_volume", "quoteAssetVolume",
        "volume_quote", "Volume USDT", "volume_usdt", "qv"
    ]
    for c in candidates:
        if c in df.columns:
            return df[c]
    # Fallback: si hay base 'volume' y 'close', aproximar
    if "volume" in df.columns and "close" in df.columns:
        return df["volume"].astype(float) * df["close"].astype(float)
    if "Volume" in df.columns and "Close" in df.columns:
        return df["Volume"].astype(float) * df["Close"].astype(float)
    return None


class IndicadoresTecnicos:
    """
    Calcula indicadores técnicos sobre marcos Diario y Semanal:
    - EMAs: 20/50/200 (D) y 20/50 (W)
    - RSI(14) D/W
    - ADX(14) D/W
    - ATR(14) D y ATR% (ATR/close)
    - Volumen USDT (última vela diaria, si está disponible)

    ACEPTA **kwargs** y los ignora de forma segura para ser compatible con
    llamadas previas que pasaban 'ema20_d', etc. Además, expone atributos
    homónimos calculados internamente para minimizar cambios aguas arriba.

    df_d y df_w deben contener columnas OHLC (nombres configurables).
    """

    def __init__(
        self,
        df_d: pd.DataFrame,
        df_w: pd.DataFrame,
        *,
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,  # <- clave del #1: tragamos kwargs sin romper
    ) -> None:
        self.config = {
            "cols": {"open": "open", "high": "high", "low": "low", "close": "close"},
            "ema_spans_d": (20, 50, 200),
            "ema_spans_w": (20, 50),
            "rsi_period": 14,
            "adx_period": 14,
            "atr_period": 14,
            "trend_confirm_bars": 1,  # cuántas velas mirar para tendencia simple
        }
        if config:
            # mezcla superficial
            self.config.update(config)
            if "cols" in config:
                self.config["cols"].update(config["cols"])

        self.kwargs_pasados = dict(kwargs or {})  # guardamos por auditoría (no usados)

        # Copias seguras (ordenar por tiempo por si acaso)
        self.df_d = (df_d or pd.DataFrame()).copy()
        self.df_w = (df_w or pd.DataFrame()).copy()
        for df in (self.df_d, self.df_w):
            if not df.empty and "time" in df.columns:
                df.sort_values("time", inplace=True)

        self._calc_all()

    # --------- Cálculos principales ---------

    def _calc_all(self) -> None:
        cols = self.config["cols"]
        rsi_p = int(self.config["rsi_period"])
        adx_p = int(self.config["adx_period"])
        atr_p = int(self.config["atr_period"])

        # Inicializamos atributos con NaN por defecto
        self.ema20_d = np.nan
        self.ema50_d = np.nan
        self.ema200_d = np.nan
        self.ema20_w = np.nan
        self.ema50_w = np.nan

        self.rsi14_d = np.nan
        self.rsi14_w = np.nan

        self.adx14_d = np.nan
        self.adx14_w = np.nan

        self.atr14_d = np.nan
        self.atr_pct_d = np.nan

        self.close_d = np.nan
        self.close_w = np.nan

        self.volume_usdt_24h = np.nan

        # Si df diario está presente, calculamos
        if not self.df_d.empty:
            close_d = _col(self.df_d, "close", cols).astype(float)
            self.close_d = _last(close_d)

            # EMAs diarias
            span_d = self.config["ema_spans_d"]
            ema_d1 = _ema(close_d, span_d[0]) if len(close_d) >= span_d[0] else pd.Series(dtype=float)
            ema_d2 = _ema(close_d, span_d[1]) if len(close_d) >= span_d[1] else pd.Series(dtype=float)
            ema_d3 = _ema(close_d, span_d[2]) if len(close_d) >= span_d[2] else pd.Series(dtype=float)

            self.ema20_d = _last(ema_d1) if not ema_d1.empty else np.nan
            self.ema50_d = _last(ema_d2) if not ema_d2.empty else np.nan
            self.ema200_d = _last(ema_d3) if not ema_d3.empty else np.nan

            # RSI y ADX diarios
            rsi_d = _rsi(close_d, rsi_p) if len(close_d) >= rsi_p else pd.Series(dtype=float)
            self.rsi14_d = _last(rsi_d) if not rsi_d.empty else np.nan

            try:
                adx_d_full = _adx(self.df_d, adx_p, cols) if len(self.df_d) >= adx_p + 1 else pd.Series(dtype=float)
            except Exception:
                adx_d_full = pd.Series(dtype=float)
            self.adx14_d = _last(adx_d_full) if not adx_d_full.empty else np.nan

            # ATR diario
            try:
                atr_d_full = _atr(self.df_d, atr_p, cols) if len(self.df_d) >= atr_p + 1 else pd.Series(dtype=float)
            except Exception:
                atr_d_full = pd.Series(dtype=float)
            self.atr14_d = _last(atr_d_full) if not atr_d_full.empty else np.nan
            self.atr_pct_d = float(self.atr14_d / self.close_d) if np.isfinite(self.atr14_d) and self.close_d else np.nan

            # Volumen USDT (última vela)
            qv = _infer_quote_volume(self.df_d)
            if qv is not None and not qv.empty:
                self.volume_usdt_24h = _last(qv)

        # Semanal
        if not self.df_w.empty:
            close_w = _col(self.df_w, "close", self.config["cols"]).astype(float)
            self.close_w = _last(close_w)

            span_w = self.config["ema_spans_w"]
            ema_w1 = _ema(close_w, span_w[0]) if len(close_w) >= span_w[0] else pd.Series(dtype=float)
            ema_w2 = _ema(close_w, span_w[1]) if len(close_w) >= span_w[1] else pd.Series(dtype=float)

            self.ema20_w = _last(ema_w1) if not ema_w1.empty else np.nan
            self.ema50_w = _last(ema_w2) if not ema_w2.empty else np.nan

            rsi_w = _rsi(close_w, int(self.config["rsi_period"])) if len(close_w) >= rsi_p else pd.Series(dtype=float)
            self.rsi14_w = _last(rsi_w) if not rsi_w.empty else np.nan

            try:
                adx_w_full = _adx(self.df_w, int(self.config["adx_period"]), self.config["cols"]) if len(self.df_w) >= adx_p + 1 else pd.Series(dtype=float)
            except Exception:
                adx_w_full = pd.Series(dtype=float)
            self.adx14_w = _last(adx_w_full) if not adx_w_full.empty else np.nan

    # --------- Tendencias / helpers de alto nivel ---------

    @property
    def tendencia_diaria(self) -> str:
        """
        Clasificación simple:
        - 'Alcista' si close > ema20_d > ema50_d (o close>ema200_d si 200 disponible).
        - 'Bajista' si close < ema20_d < ema50_d (o close<ema200_d).
        - 'Lateral' en el resto.
        """
        c = self.close_d
        e20 = self.ema20_d
        e50 = self.ema50_d
        e200 = self.ema200_d

        if np.isfinite(c) and np.isfinite(e20) and np.isfinite(e50):
            if c > e20 > e50:
                return "Alcista"
            if c < e20 < e50:
                return "Bajista"

        if np.isfinite(c) and np.isfinite(e200):
            if c > e200:
                return "Alcista"
            if c < e200:
                return "Bajista"

        return "Lateral"

    @property
    def tendencia_semanal(self) -> str:
        c = self.close_w
        e20w = self.ema20_w
        e50w = self.ema50_w
        if np.isfinite(c) and np.isfinite(e20w) and np.isfinite(e50w):
            if c > e20w > e50w:
                return "Alcista"
            if c < e20w < e50w:
                return "Bajista"
        return "Lateral"

    # --------- API segura para upstream ---------

    def to_dict(self) -> Dict[str, Any]:
        """Exporta todos los indicadores clave como diccionario (para CSV/Telegram)."""
        return {
            "close_d": self.close_d,
            "close_w": self.close_w,
            "ema20_d": self.ema20_d,
            "ema50_d": self.ema50_d,
            "ema200_d": self.ema200_d,
            "ema20_w": self.ema20_w,
            "ema50_w": self.ema50_w,
            "rsi14_d": self.rsi14_d,
            "rsi14_w": self.rsi14_w,
            "adx14_d": self.adx14_d,
            "adx14_w": self.adx14_w,
            "atr14_d": self.atr14_d,
            "atr_pct_d": self.atr_pct_d,
            "volume_usdt_24h": self.volume_usdt_24h,
            "tendencia_d": self.tendencia_diaria,
            "tendencia_w": self.tendencia_semanal,
        }

    # Asegura compatibilidad si upstream intentó acceder a un kw pasado:
    def __getattr__(self, item: str) -> Any:
        """
        Si upstream hacía algo como indicadores.ema20_d tras pasarla como kw,
        garantizamos que exista devolviendo el atributo calculado o, en última
        instancia, mirando en kwargs_pasados.
        """
        if item in self.__dict__:
            return self.__dict__[item]
        if item in self.kwargs_pasados:
            return self.kwargs_pasados[item]
        # Como fallback final, devolvemos NaN para nombres "parecidos"
        if any(item.startswith(prefix) for prefix in ("ema", "rsi", "adx", "atr")):
            return np.nan
        raise AttributeError(item)
