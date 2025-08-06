import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)

def get_macro_data(period: str = "5d", interval: str = "1d") -> dict:
    result = {"VIX": None, "DXY": None}

    try:
        vix = yf.download("^VIX", period=period, interval=interval, progress=False)
        if not vix.empty:
            result["VIX"] = round(vix["Close"].iloc[-1].item(), 2)
            logging.info(f"✅ VIX cargado: {result['VIX']}")
        else:
            logging.warning("⚠️ VIX está vacío")
    except Exception as e:
        logging.error(f"❌ Error VIX: {e}")

    try:
        dxy = yf.download("UUP", period=period, interval=interval, progress=False)
        if not dxy.empty:
            result["DXY"] = round(dxy["Close"].iloc[-1].item(), 2)
            logging.info(f"✅ DXY (UUP) cargado: {result['DXY']}")
        else:
            logging.warning("⚠️ DXY (UUP) está vacío")
    except Exception as e:
        logging.error(f"❌ Error DXY/UUP: {e}")

    return result

if __name__ == "__main__":
    datos = get_macro_data()
    print("\n📊 RESULTADO FINAL:")
    print(datos)

