# notifier/sender.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.logger import get_audit_logger
from notifier.telegram import TelegramNotifier

# --- Intenta leer config (valores por defecto si no existe) ---
try:
    import config  # type: ignore
except Exception:
    class _Cfg:
        MIN_SCORE_ALERTA = 55.0
        SEND_TOP_N = 5
        COOLDOWN_MINUTES = 30
        EXCLUDE_SYMBOLS = []
        TELEGRAM_BOT_TOKEN = ""
        TELEGRAM_TOKEN = ""
        TELEGRAM_CHAT_ID = ""
        TELEGRAM_TIMEOUT = 10
    config = _Cfg()  # type: ignore

audit = get_audit_logger()


# ======================= utilidades =======================

def _now_ts() -> float:
    return time.time()

def _get_cfg(name: str, default: Any) -> Any:
    return getattr(config, name, default)

def _as_float(x, default: Optional[float] = None) -> Optional[float]:
    try:
        v = float(x)
        if v != v:  # NaN
            return default
        return v
    except Exception:
        return default


# ======================= estado persistente =======================

class SenderState:
    """
    Maneja el estado de últimos envíos por (symbol|bias) para aplicar cooldown entre ejecuciones.
    """
    def __init__(self, path: Optional[str] = None) -> None:
        if path is None:
            # Guardamos el estado junto a este archivo por simplicidad
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "sender_state.json")
        self.path = path
        self.data: Dict[str, Any] = {"last_sent": {}}  # {"BTCUSDT|LONG": ts, ...}
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        self.data.update(raw)
        except Exception:
            # Estado corrupto → reiniciamos
            self.data = {"last_sent": {}}

    def save(self) -> None:
        try:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            pass

    # API
    def last_sent_ts(self, symbol: str, bias: str) -> Optional[float]:
        key = f"{symbol}|{bias}"
        ts = self.data.get("last_sent", {}).get(key)
        return float(ts) if ts is not None else None

    def mark_sent(self, symbol: str, bias: str, ts: Optional[float] = None) -> None:
        key = f"{symbol}|{bias}"
        self.data.setdefault("last_sent", {})[key] = float(ts or _now_ts())


# ======================= normalización de candidatos =======================

@dataclass
class CandidateView:
    symbol: str
    bias: str
    score: float
    entry: float
    stop_loss: float
    take_profit: float
    atr_pct: Optional[float] = None
    rr: Optional[float] = None
    adx: Optional[float] = None
    volume_usdt_24h: Optional[float] = None
    # breakdown opcional
    trend_score: Optional[float] = None
    volume_score: Optional[float] = None
    momentum_score: Optional[float] = None
    volatility_score: Optional[float] = None
    rr_score: Optional[float] = None

    @staticmethod
    def from_obj(obj: Any) -> "CandidateView":
        """
        Acepta el contenedor devuelto por analyzer (SimpleNamespace o clase) o un dict.
        """
        g = (obj.get if isinstance(obj, dict) else lambda k, d=None: getattr(obj, k, d))

        symbol = str(g("symbol", ""))
        bias = str(g("bias", g("tipo", "LONG"))).upper()
        score = float(g("score", 0.0) or 0.0)

        # niveles
        entry = _as_float(g("entry", g("entry_price", g("precio", None))), 0.0) or 0.0
        sl = _as_float(g("stop_loss", g("sl", None)), 0.0) or 0.0
        tp = _as_float(g("take_profit", g("stop_profit", g("tp", None))), 0.0) or 0.0

        atr_pct = _as_float(g("atr_pct", None))
        rr = _as_float(g("rr", None))
        adx = _as_float(g("adx", None))
        vol = _as_float(g("volume_usdt_24h", g("volumen_usdt_24h", None)))

        # breakdown (si viene del analyzer nuevo)
        t_s = _as_float(g("trend_score", None))
        v_s = _as_float(g("volume_score", None))
        m_s = _as_float(g("momentum_score", None))
        vo_s = _as_float(g("volatility_score", None))
        rr_s = _as_float(g("rr_score", None))

        return CandidateView(
            symbol=symbol,
            bias=bias,
            score=score,
            entry=entry,
            stop_loss=sl,
            take_profit=tp,
            atr_pct=atr_pct,
            rr=rr,
            adx=adx,
            volume_usdt_24h=vol,
            trend_score=t_s,
            volume_score=v_s,
            momentum_score=m_s,
            volatility_score=vo_s,
            rr_score=rr_s,
        )


# ======================= formateo payload Telegram =======================

def _build_context_lines(c: CandidateView) -> List[str]:
    """
    Líneas opcionales de contexto para TelegramNotifier (se muestran con bullets).
    TelegramNotifier ya añade ATR% y RR≈ si no están, pero aquí aportamos señales claras.
    """
    ctx: List[str] = []
    if c.adx is not None:
        ctx.append(f"ADX={c.adx:.2f}")
    # Puntuaciones internas si existen
    parts: List[str] = []
    if c.trend_score is not None:
        parts.append(f"T{c.trend_score:.1f}")
    if c.momentum_score is not None:
        parts.append(f"M{c.momentum_score:.1f}")
    if c.volatility_score is not None:
        parts.append(f"Vola{c.volatility_score:.1f}")
    if c.volume_score is not None:
        parts.append(f"Vol{c.volume_score:.1f}")
    if c.rr_score is not None:
        parts.append(f"RRs{c.rr_score:.1f}")
    if parts:
        ctx.append("Scores: " + " / ".join(parts))
    # Liquidez (redondeo grande)
    if c.volume_usdt_24h and c.volume_usdt_24h > 0:
        try:
            if c.volume_usdt_24h >= 1_000_000:
                ctx.append(f"Vol24h≈{c.volume_usdt_24h:,.0f} USDT")
            else:
                ctx.append(f"Vol24h≈{c.volume_usdt_24h:.0f} USDT")
        except Exception:
            pass
    return ctx


def _to_telegram_payload(
    c: CandidateView,
    *,
    evaluated_total: Optional[int],
    eligible_total: Optional[int],
    sent_so_far: int,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Adapta CandidateView al payload que espera TelegramNotifier.send_signal().
    """
    payload: Dict[str, Any] = {
        "symbol": c.symbol,
        "bias": c.bias,
        "score": c.score,
        "entry": c.entry,
        "stop_loss": c.stop_loss,
        "take_profit": c.take_profit,
        # footer
        "evaluated": int(evaluated_total) if evaluated_total is not None else None,
        "eligible": int(eligible_total) if eligible_total is not None else None,
        "sent": int(sent_so_far),
        # contexto
        "context": _build_context_lines(c),
    }
    # ATR% explícito si lo tenemos (TelegramNotifier también lo sabe extraer)
    if c.atr_pct is not None:
        payload["atr_pct"] = c.atr_pct

    # Overrides opcionales del step dinámico o de límites de grids (si quisieras)
    if overrides:
        payload.update(overrides)

    return payload


# ======================= clase principal =======================

class Sender:
    """
    Orquestador de envíos a Telegram con cooldown, top-N y exclusiones.
    """
    def __init__(
        self,
        notifier: TelegramNotifier,
        *,
        state_path: Optional[str] = None,
        min_score: Optional[float] = None,
        send_top_n: Optional[int] = None,
        cooldown_minutes: Optional[int] = None,
        exclude_symbols: Optional[Iterable[str]] = None,
    ) -> None:
        self.notifier = notifier
        self.state = SenderState(state_path)

        self.min_score = float(min_score if min_score is not None else _get_cfg("MIN_SCORE_ALERTA", 55.0))
        self.send_top_n = int(send_top_n if send_top_n is not None else _get_cfg("SEND_TOP_N", 5))
        self.cooldown_minutes = int(cooldown_minutes if cooldown_minutes is not None else _get_cfg("COOLDOWN_MINUTES", 30))

        ex = exclude_symbols if exclude_symbols is not None else _get_cfg("EXCLUDE_SYMBOLS", [])
        self.exclude_symbols = set([s.upper() for s in (ex or [])])

    # --------------- helpers ---------------

    def _is_excluded(self, symbol: str) -> bool:
        return symbol.upper() in self.exclude_symbols

    def _cooldown_ok(self, symbol: str, bias: str) -> bool:
        last = self.state.last_sent_ts(symbol, bias)
        if last is None:
            return True
        wait_s = self.cooldown_minutes * 60
        return (_now_ts() - last) >= wait_s

    def _eligible_by_rules(self, c: CandidateView) -> Tuple[bool, Optional[str]]:
        if self._is_excluded(c.symbol):
            return False, "excluido por configuración"
        if c.score < self.min_score:
            return False, f"score {c.score:.2f} < {self.min_score:.2f}"
        if not self._cooldown_ok(c.symbol, c.bias):
            return False, "en cooldown"
        return True, None

    def _sort_key(self, c: CandidateView) -> Tuple[float, float, float]:
        """
        Orden principal por score; desempates por ADX y volumen 24h (si existen).
        """
        adx = c.adx if c.adx is not None else -1.0
        vol = c.volume_usdt_24h if c.volume_usdt_24h is not None else -1.0
        return (c.score, adx, vol)

    # --------------- API pública ---------------

    def send_batch(
        self,
        raw_candidates: Iterable[Any],
        *,
        evaluated_total: Optional[int] = None,
        overrides: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Envía una tanda a Telegram:
        - raw_candidates: lista de objetos (o dicts) devueltos por analyzer.
        - evaluated_total: total de símbolos evaluados (para pie del mensaje).
        - overrides: dict con ajustes de grids (ej. {"min_step_pct":0.015, "max_step_pct":0.035, "min_grids":6, "max_grids":30})
        - dry_run: si True, no envía; solo simula.
        Devuelve {evaluated, eligible, to_send, sent_ok, sent_fail, skipped}.
        """
        # Normaliza
        cvs: List[CandidateView] = []
        for obj in (raw_candidates or []):
            try:
                cvs.append(CandidateView.from_obj(obj))
            except Exception:
                pass

        if evaluated_total is None:
            evaluated_total = len(cvs)  # si no nos pasan el total real, usamos el tamaño de entrada

        # Regla de elegibilidad + cooldown
        eligible: List[CandidateView] = []
        skipped: List[Tuple[str, str]] = []
        for c in cvs:
            ok, reason = self._eligible_by_rules(c)
            if ok:
                eligible.append(c)
            else:
                skipped.append((f"{c.symbol}({c.bias})", reason or "motivo desconocido"))

        # Orden y top-N
        eligible.sort(key=self._sort_key, reverse=True)
        to_send = eligible[: max(0, int(self.send_top_n))]

        # Envío
        sent_ok, sent_fail = 0, 0
        sent_symbols: List[str] = []

        for idx, c in enumerate(to_send, start=1):
            payload = _to_telegram_payload(
                c,
                evaluated_total=evaluated_total,
                eligible_total=len(eligible),
                sent_so_far=sent_ok,  # se irá actualizando
                overrides=overrides,
            )

            if dry_run:
                audit.info(f"[DRY RUN] {c.symbol} {c.bias} score={c.score:.2f} → NO enviado")
                sent_ok += 1  # contamos como 'simulado'
                sent_symbols.append(c.symbol)
                continue

            try:
                ok = self.notifier.send_signal(payload)
                if ok:
                    sent_ok += 1
                    sent_symbols.append(c.symbol)
                    self.state.mark_sent(c.symbol, c.bias)
                    audit.info(f"Telegram OK → {c.symbol} (score {c.score:.2f})")
                else:
                    sent_fail += 1
                    audit.info(f"Telegram FAIL → {c.symbol} (score {c.score:.2f})")
            except Exception as e:
                sent_fail += 1
                audit.info(f"Telegram EXC → {c.symbol}: {e}")

        # Persistimos estado si hubo envíos reales
        if not dry_run and (sent_ok > 0 or sent_fail > 0):
            self.state.save()

        # Resumen de consola
        audit.info(
            f"✅ Enviados a Telegram: {sent_ok}/{len(to_send)}"
        )

        return {
            "evaluated": int(evaluated_total or 0),
            "eligible": int(len(eligible)),
            "to_send": int(len(to_send)),
            "sent_ok": int(sent_ok),
            "sent_fail": int(sent_fail),
            "skipped": skipped,
            "sent_symbols": sent_symbols,
        }


# ======================= factoría rápida =======================

def build_sender_from_config() -> Sender:
    """
    Crea un Sender leyendo credenciales y límites desde config.
    Busca TELEGRAM_BOT_TOKEN o TELEGRAM_TOKEN y TELEGRAM_CHAT_ID.
    """
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "") or getattr(config, "TELEGRAM_TOKEN", "")
    chat_id = getattr(config, "TELEGRAM_CHAT_ID", "")
    timeout = int(getattr(config, "TELEGRAM_TIMEOUT", 10) or 10)
    if not token or not chat_id:
        raise RuntimeError("Config incompleta: define TELEGRAM_BOT_TOKEN (o TELEGRAM_TOKEN) y TELEGRAM_CHAT_ID")

    notifier = TelegramNotifier(token=token, chat_id=chat_id, timeout=timeout)

    return Sender(
        notifier=notifier,
        state_path=None,  # usa sender_state.json por defecto junto a este archivo
        min_score=_get_cfg("MIN_SCORE_ALERTA", 55.0),
        send_top_n=_get_cfg("SEND_TOP_N", 5),
        cooldown_minutes=_get_cfg("COOLDOWN_MINUTES", 30),
        exclude_symbols=_get_cfg("EXCLUDE_SYMBOLS", []),
    )
