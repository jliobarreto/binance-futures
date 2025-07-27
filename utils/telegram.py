import requests
import logging
from typing import Any
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from data.models import IndicadoresTecnicos


def formatear_senal(data: Any) -> str:
    """Devuelve un mensaje de varias líneas con formato Markdown.

    ``data`` puede ser una instancia de :class:`IndicadoresTecnicos` o un
    diccionario con las claves necesarias.  Se extraen los valores básicos de
    la señal (símbolo, tipo, precios) y, si están disponibles, los indicadores
    ``RSI``, ``MACD``, ``Vitalidad`` y ``Grids``.
    """

    if isinstance(data, IndicadoresTecnicos):
        symbol = data.symbol
        tipo = data.tipo
        precio = data.precio
        tp = data.tp
        sl = data.sl
        score = getattr(data, "score", None)
        rsi = getattr(data, "rsi_1d", None)
        macd_up = getattr(data, "macd_1d", None)
        macd_signal = getattr(data, "macd_signal_1d", None)
        vitalidad = (
            data.volumen_actual / data.volumen_promedio
            if getattr(data, "volumen_promedio", 0)
            else None
        )
        grids = getattr(data, "grids", None)
    elif isinstance(data, dict):
        symbol = data.get("Criptomoneda")
        tipo = data.get("Señal")
        precio = data.get("Precio")
        tp = data.get("TP")
        sl = data.get("SL")
        score = data.get("Score")
        rsi = data.get("RSI")
        macd_up = data.get("MACD")  # Puede ser valor o dirección
        macd_signal = data.get("MACD_signal")
        vitalidad = data.get("Vitalidad")
        grids = data.get("Grids")
    else:
        raise TypeError("Objeto no soportado para formatear_senal")

    # Dirección del MACD en texto
    direccion_macd = ""
    try:
        if macd_signal is not None:
            direccion_macd = (
                "alcista" if float(macd_up) > float(macd_signal) else "bajista"
            )
        elif macd_up is not None:
            direccion_macd = str(macd_up)
    except Exception:
        direccion_macd = str(macd_up)

    lineas = [
        "🚨 SEÑAL DE COMPRA" if tipo == "LONG" else "🚨 SEÑAL DE VENTA",
        f"🪙 Criptomoneda: {symbol}",
        f"🤖 Señal: {tipo}",
        f"📈 Precio de entrada: ${precio:.4f}",
        f"🎯 Take profit: ${tp:.4f}",
        f"🛑 Stop Loss: ${sl:.4f}",
    ]

    if rsi is not None:
        lineas.append(
            f"📊 RSI: {float(rsi):.1f} | MACD {direccion_macd}" if direccion_macd else f"📊 RSI: {float(rsi):.1f}"
        )
    elif direccion_macd:
        lineas.append(f"📊 MACD {direccion_macd}")

    if vitalidad is not None:
        try:
            lineas.append(f"⚡ Vitalidad: {float(vitalidad):.2f}x")
        except (ValueError, TypeError):
            lineas.append(f"⚡ Vitalidad: {vitalidad}")

    if grids is not None:
        lineas.append(f"📐 Grids: {grids}")

    if score is not None:
        try:
            punt = float(score)
            if punt >= 50:
                comentario = "🟢 Señal excelente"
            elif punt >= 40:
                comentario = "🟡 Señal buena"
            else:
                comentario = None
        except Exception:
            comentario = None
        if comentario:
            lineas.append(comentario)

    return "\n".join(lineas)


def enviar_telegram(texto: str, parse_mode: str = "Markdown") -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Faltan credenciales de Telegram")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Error enviando mensaje a Telegram: {e}")


def enviar_telegram_con_botones(texto: str, botones: list) -> str:
    """Envía un mensaje con botones de respuesta rápida.

    Cada botón es una opción como 'Cuenta 1', 'Cuenta 2', 'Rechazada'.
    """

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Faltan credenciales de Telegram")
        return ""

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = [[{"text": b, "callback_data": b}] for b in botones]
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": keyboard},
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info("Respuesta de Telegram: %s", data)
        return str(data.get("result", {}).get("message_id"))
    except Exception as e:
        logging.error(f"Error enviando mensaje con botones: {e}")
        return ""
  
def responder_callback(callback_id: str, text: str) -> None:
    """Envía answerCallbackQuery para confirmar el callback en Telegram."""
    if not TELEGRAM_TOKEN:
        logging.error("Faltan credenciales de Telegram")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id, "text": text}
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        logging.info("Respuesta answerCallbackQuery: %s", response.json())
    except Exception as e:
        logging.error(f"Error respondiendo callback: {e}")
