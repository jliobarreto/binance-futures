# notifier.py
import os
import requests
from openpyxl import Workbook, load_workbook
from datetime import datetime
from utils.path import XLSX_PATH
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# XLSX_PATH ya contiene la ruta completa del archivo, por lo que solo
# es necesario convertirlo a cadena para usarlo con openpyxl.
SIGNAL_FILE = str(XLSX_PATH)


def enviar_telegram(texto: str, buttons: list = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }

    if buttons:
        keyboard = [[{"text": b, "callback_data": b}] for b in buttons]
        payload["reply_markup"] = {"inline_keyboard": keyboard}

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return None
