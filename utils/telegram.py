import logging
from typing import Any, Optional

import requests
import config
from data import IndicadoresTecnicos


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
    """Formatea con decimales según magnitud (útil para spot/futuros)."""
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

def _escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ───────────────────────── formato de señal ─────────────────────────

def formatear_senal(data: Any, parse_mode: str = "HTML") -> str:
    """
    Devuelve un mensaje multi-línea listo para Telegram.

    Acepta:
      - IndicadoresTecnicos con attrs: symbol, tipo/bias, precio/entry, sl, tp/take_profit/stop_profit, score, rsi_1d, macd_1d, macd_signal_1d, volumen_actual, volumen_promedio, grids.
      - dict con claves equivalentes.

    Muestra: Entry, StopLoss y Stop Profit (único).
    """
    # ---- 1) Extraer datos robustamente
    if isinstance(data, IndicadoresTecnicos):
        symbol = getattr(data, "symbol", None)
        tipo = getattr(data, "tipo", getattr(data, "bias", None))
        precio = _safe_float(getattr(data, "precio", None))
        entry = _safe_float(getattr(data, "entry", precio))
        sl = _safe_float(getattr(data, "sl", getattr(data, "stop_loss", None)))
        # aceptar tp/take_profit/stop_profit
        sp = _safe_float(
            getattr(data, "tp",
                    getattr(data, "take_profit",
                            getattr(data, "stop_profit", None)))
        )
        score = _safe_float(getattr(data, "score", None))
        rsi = _safe_float(getattr(data, "rsi_1d", None))
        macd_up = _safe_float(getattr(data, "macd_1d", None))
        macd_signal = _safe_float(getattr(data, "macd_signal_1d", None))
        vitalidad = None
        try:
            va = _safe_float(getattr(data, "volumen_actual", None))
            vp = _safe_float(getattr(data, "volumen_promedio", None))
            vitalidad = (va / vp) if (va and vp and vp > 0) else None
        except Exception:
            pass
        grids = getattr(data, "grids", None)
    elif isinstance(data, dict):
        symbol = data.get("Criptomoneda") or data.get("symbol")
        tipo = data.get("Señal") or data.get("tipo") or data.get("bias")
        precio = _safe_float(data.get("Precio") or data.get("close") or data.get("precio"))
        entry = _safe_float(data.get("entry", precio))
        sl = _safe_float(data.get("SL") or data.get("stop_loss") or data.get("sl"))
        sp = _safe_float(data.get("TP") or data.get("take_profit") or data.get("stop_profit"))
        score = _safe_float(data.get("Score") or data.get("score"))
        rsi = _safe_float(data.get("RSI") or data.get("rsi_1d"))
        macd_up = _safe_float(data.get("MACD") or data.get("macd_1d"))
        macd_signal = _safe_float(data.get("MACD_signal") or data.get("macd_signal_1d"))
        vitalidad = _safe_float(data.get("Vitalidad"))
        grids = data.get("Grids")
    else:
        raise TypeError("Objeto no soportado para formatear_senal")

    symbol_s = _escape_html(symbol or "—")
    tipo_s = (str(tipo).upper() if tipo else "—")
    # Dirección del MACD (si disponible)
    direccion_macd = ""
    if macd_up is not None and macd_signal is not None:
        direccion_macd = "alcista" if macd_up > macd_signal else "bajista"

    # Calcula RR si hay entry/sl/sp
    rr_txt = ""
    if entry is not None and sl is not None and sp is not None:
        r = abs(entry - sl)
        if r > 0:
            rr = abs(sp - entry) / r
            rr_txt = f" (≈{rr:.2f}R)"

    # Título según tipo
    encabezado = "🚨 SEÑAL DE COMPRA" if tipo_s == "LONG" else "🚨 SEÑAL DE VENTA"

    # ---- 2) Construir mensaje (HTML por defecto)
    lineas = [
        _escape_html(encabezado),
        f"🪙 <b>Criptomoneda:</b> {symbol_s}",
        f"🤖 <b>Señal:</b> {_escape_html(tipo_s)}",
        f"🔹 <b>Entry:</b> ${_fmt_price(entry)}",
        f"🛑 <b>Stop Loss:</b> ${_fmt_price(sl)}",
        f"🟩 <b>Stop Profit:</b> ${_fmt_price(sp)}{_escape_html(rr_txt)}",
    ]

    if rsi is not None or direccion_macd:
        stats = []
        if rsi is not None:
            stats.append(f"RSI {rsi:.1f}")
        if direccion_macd:
            stats.append(f"MACD {direccion_macd}")
        lineas.append(f"📊 <b>Momentum:</b> {_escape_html(' | '.join(stats))}")

    if vitalidad is not None:
        lineas.append(f"⚡ <b>Vitalidad:</b> {vitalidad:.2f}×")

    if grids is not None:
        lineas.append(f"📐 <b>Grids:</b> {_escape_html(grids)}")

    if score is not None:
        try:
            punt = float(score)
            if punt >= 70:
                comentario = "🟢 Señal fuerte"
            elif punt >= 55:
                comentario = "🟡 Señal viable"
            else:
                comentario = None
        except Exception:
            comentario = None
        if comentario:
            lineas.append(comentario)

    return "\n".join(lineas)


# ───────────────────────── envío a Telegram ─────────────────────────

def enviar_telegram(
    texto: str,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
    thread_id: Optional[int] = None,
) -> None:
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
        # Mejor enviar como JSON (evita problemas de encoding)
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Error enviando mensaje a Telegram: {e}")


def enviar_telegram_con_botones(
    texto: str,
    botones: list[str],
    parse_mode: str = "HTML",
    thread_id: Optional[int] = None,
) -> str:
    """
    Envía un mensaje con botones inline (ej.: 'Cuenta 1', 'Cuenta 2', 'Rechazada').
    Devuelve el message_id si tuvo éxito.
    """
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
    """Confirma el callback en Telegram (cuando ya uses webhooks)."""
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
