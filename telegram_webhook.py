from flask import Flask, request, jsonify
from notifier import manejar_callback
from logic.memory import operaciones_enviadas

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback["data"]
        symbol = callback_data.split('|')[1]
        manejar_callback(callback_data, symbol, operaciones_enviadas)

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=5000)  
