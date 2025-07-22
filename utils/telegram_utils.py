import requests
import logging
from typing import Any
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from data.models import IndicadoresTecnicos


def formatear_senal(data: Any) -> str:
    """Construye un mensaje de varias líneas para Telegram.

    Acepta un objeto ``IndicadoresTecnicos`` o un diccionario con
    las claves básicas de la señal y retorna una cadena formateada.
    """
    if isinstance(data, IndicadoresTecnicos):
        symbol = data.symbol
        tipo = data.tipo
        precio = data.precio
        tp = data.tp
        sl = data.sl
        score = getattr(data, "score", None)
    elif isinstance(data, dict):
        symbol = data.get("Criptomoneda")
        tipo = data.get("Señal")
        precio = data.get("Precio")
        tp = data.get("TP")
        sl = data.get("SL")
        score = data.get("Score")
    else:
        raise TypeError("Objeto no soportado para formatear_senal")

    lineas = [
        f"\ud83d\udcc8 *{symbol}*",  # 📈
        f"Tipo: {tipo}",
        f"Entrada: {precio:.4f}",
        f"TP: {tp:.4f}",
        f"SL: {sl:.4f}",
    ]
    if score is not None:
        try:
            lineas.append(f"Score: {float(score):.2f}")
        except (ValueError, TypeError):
            lineas.append(f"Score: {score}")

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
    """
    Envía un mensaje con botones de respuesta rápida.
    Cada botón es una opción como 'Cuenta 1', 'Cuenta 2', 'Rechazada'.
    Retorna el mensaje_id si fue exitoso.
    """
