# notifier/telegram.py
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, List

import requests
import config

# ───────────────────────── helpers ─────────────────────────

def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None

def _fmt_price(x: Optional[float]) -> str:
    """Formatea con decimales según magnitud (cubre la mayoría de símbolos)."""
    if x is None:
        return "—"
    ax = abs(x)
    if ax >= 100:
        return f"{x:.2f}"
    if ax >= 1:
        return f"{x:.4f}"
    if ax >= 0.01:
        return f"{x:.5f}"
    return f"{x:.8f}"

def _format_signal_text(s: Dict) -> str:
    """
    Construye el mensaje en Markdown.
    Espera en s: symbol, bias, entry, stop_loss, (take_profit o stop_profit), score, timeframe, context(list[str])
    """
    symbol = s.get("symbol", "—")
    bias = (s.get("bias") or "—").upper()
    entry = _safe_float(s.get("entry"))
    sl = _safe_float(s.get("stop_loss"))
    tp = _safe_float(s.get("take_profit", s.get("stop_profit")))

    rr_txt = ""
    if entry is not None and sl is not None and tp is not None:
        r = abs(entry - sl)
        if r > 0:
            rr = abs(tp - entry) / r
            rr_txt = f" (≈{rr:.2f}R)"

    header_emoji = "🟢" if bias == "LONG" else "🔴"
    tf = s.get("timeframe", "1d/1w")
    score = s.get("score", "?")
    ctx_lines: List[str] = s.get("context", []) or []
    ctx = "\n".join(f"• {c}" for c in ctx_lines)

    return (
        f"{header_emoji} *FUTURES SIGNAL* – {tf}\n"
        f"*{symbol}* ({bias}) — *Score:* {score}\n\n"
        f"*Entry:* `{_fmt_price(entry)}`\n"
        f"*StopLoss:* `{_fmt_price(sl)}`\n"
        f"*StopProfit:* `{_fmt_price(tp)}`{rr_txt}\n"
        + (f"\n*Contexto:*\n{ctx}" if ctx else "")
    )

# ───────────────────────── clase OO (opcional) ─────────────────────────

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout: int = 15):
        self.base = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send_signal(self, signal: Dict, retry: int = 2) -> bool:
        text = _format_signal_text(signal)
        payload = {
            "chat_id": str(self.chat_id),
            "text": text,
            "parse_mode": "Markdown",
        }
        for i in range(retry + 1):
            try:
                r = requests.post(self.base, json=payload, timeout=self.timeout)
                if r.ok:
                    return True
            except Exception as e:
                logging.warning("Fallo envío Telegram (intento %s): %s", i + 1, e)
            time.sleep(1 + i)
        return False

# ───────────────────────── wrappers de compatibilidad ─────────────────────────

def formatear_senal(data: Any) -> str:
    """
    Acepta:
      - dataclass IndicadoresTecnicos
      - dict con claves: symbol/bias/entry/stop_loss/(take_profit|stop_profit)/score/context/timeframe
    """
    try:
        from data.models import IndicadoresTecnicos
    except Exception:
        IndicadoresTecnicos = object  # type: ignore

    if isinstance(data, dict):
        s: Dict = {
            "symbol": data.get("symbol") or data.get("Criptomoneda"),
            "bias": (data.get("bias") or data.get("Señal") or "").upper(),
            "score": data.get("score") or data.get("Score"),
            "timeframe": data.get("timeframe", "1d/1w"),
            "entry": data.get("entry") or data.get("Precio"),
            "stop_loss": data.get("stop_loss") or data.get("SL"),
            "take_profit": data.get("take_profit") or data.get("TP") or data.get("stop_profit"),
            "context": data.get("context") or [],
        }
        return _format_signal_text(s)

    if isinstance(data, IndicadoresTecnicos):
        s = {
            "symbol": getattr(data, "symbol", None),
            "bias": (getattr(data, "bias", None) or getattr(data, "tipo", "")).upper(),
            "score": getattr(data, "score", None),
            "timeframe": "1d/1w",
            "entry": getattr(data, "entry", getattr(data, "precio", None)),
            "stop_loss": getattr(data, "stop_loss", getattr(data, "sl", None)),
            "take_profit": getattr(data, "take_profit", getattr(data, "tp", None)),
            "context": [],
        }
        return _format_signal_text(s)

    raise TypeError("Objeto no soportado para formatear_senal")

def enviar_telegram(
    texto: str,
    parse_mode: str = "Markdown",
    disable_notification: bool = False,
    thread_id: Optional[int] = None,
) -> None:
    """Envía un mensaje de texto ya formateado a Telegram."""
    if not getattr(config, "TELEGRAM_TOKEN", None) or not getattr(config, "TELEGRAM_CHAT_ID", None):
        logging.error("Faltan credenciales de Telegram")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(config.TELEGRAM_CHAT_ID),
        "text": texto,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }
    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Error enviando mensaje a Telegram: {e}")

def enviar_telegram_con_botones(
    texto: str,
    botones: List[str],
    parse_mode: str = "Markdown",
    thread_id: Optional[int] = None,
) -> str:
    """Envía mensaje con botones inline. Devuelve el message_id si tuvo éxito."""
    if not getattr(config, "TELEGRAM_TOKEN", None) or not getattr(config, "TELEGRAM_CHAT_ID", None):
        logging.error("Faltan credenciales de Telegram")
        return ""

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    keyboard = [[{"text": b, "callback_data": b}] for b in botones]
    payload = {
        "chat_id": str(config.TELEGRAM_CHAT_ID),
        "text": texto,
        "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": keyboard},
    }
    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("result", {}).get("message_id", ""))
    except Exception as e:
        logging.error(f"Error enviando mensaje con botones: {e}")
        return ""

def responder_callback(callback_id: str, text: str) -> None:
    """Confirma el callback en Telegram (cuando uses webhooks)."""
    if not getattr(config, "TELEGRAM_TOKEN", None):
        logging.error("Faltan credenciales de Telegram")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id, "text": text}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Error respondiendo callback: {e}")
