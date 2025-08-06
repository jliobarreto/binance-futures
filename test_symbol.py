from logic.analyzer import analyze_symbol
from logic.indicators import load_price_data
from data.symbols import load_symbols
from logic.filters import is_market_healthy

def test():
    symbol = "BTCUSDT"
    btc_ok, eth_ok = is_market_healthy()
    print(f"🔍 Evaluando {symbol}...")

    try:
        result = analyze_symbol(symbol, btc_ok, eth_ok)
        if result:
            print(f"✅ Señal detectada para {symbol}")
            print(f"📈 Tipo: {result['Señal']} | Score: {result['Score']} | Precio: {result['Precio']}")
        else:
            print(f"⚠️ No hay señal válida para {symbol}")
    except Exception as e:
        print(f"❌ Error al analizar {symbol}: {e}")

if __name__ == "__main__":
    test()
