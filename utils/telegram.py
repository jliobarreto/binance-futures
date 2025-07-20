import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def enviar_telegram(texto: str, parse_mode: str = "Markdown") -> None:
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
        print(f"❌ Error enviando mensaje a Telegram: {e}")


def enviar_telegram_con_botones(texto: str, botones: list) -> str:
    """
    Envía un mensaje con botones de respuesta rápida.
    Cada botón es una opción como 'Cuenta 1', 'Cuenta 2', 'Rechazada'.
    Retorna el mensaje_id si fue exitoso.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = [[{"text": b, "callback_data": b}] for b in botones]
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "reply_markup": {"inline_keyboard": keyboard},
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"❌ Error enviando botones a Telegram: {e}")
        return ""


def responder_callback(callback_query_id: str, texto: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": texto
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"❌ Error respondiendo callback: {e}")
