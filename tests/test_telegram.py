from utils.telegram import formatear_senal


def test_formatear_senal_dict():
    data = {
        "Criptomoneda": "BTCUSDT",
        "Señal": "LONG",
        "Precio": 25000.0,
        "TP": 26000.0,
        "SL": 24500.0,
        "RSI": 55,
        "MACD": 1.2,
        "MACD_signal": 0.5,
        "Vitalidad": 1.3,
        "Grids": 3,
        "Score": 60,
    }
    texto = formatear_senal(data)
    assert "BTCUSDT" in texto
    assert "SEÑAL DE COMPRA" in texto
    assert "Grids" in texto
    