import os
from utils.logger import setup_logging

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)

import logging
from flask import Flask, request, jsonify

from notifier.notifier import manejar_callback
from logic.memory import operaciones_enviadas
from utils.telegram_utils import responder_callback
from utils.logger import setup_logging

MODE = os.getenv("APP_MODE", "production")
setup_logging(MODE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback.get("data", "")
        partes = callback_data.split("|")
        symbol = partes[1] if len(partes) >= 2 else ""
        try:
            manejar_callback(callback_data, symbol, operaciones_enviadas)
            responder_callback(callback.get("id", ""), "Operación recibida")
        except Exception as e:
            logging.error(f"Error procesando callback: {e}")

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=5000)
