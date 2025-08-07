import os
from .env import load_.env
from binance.client import Client

# Cargar variables del entorno
load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

if not api_key or not api_secret:
    print("❌ API Key o Secret no están definidos en el .env")
    exit(1)

try:
    client = Client(api_key, api_secret)
    # Probar llamada sencilla: obtener información de cuenta (requiere claves válidas)
    account_info = client.get_account()
    print("✅ Conexión exitosa. Información básica de cuenta:")
    print(f" - ID de cuenta: {account_info['accountType']}")
    print(f" - Cantidad de activos: {len(account_info['balances'])}")
except Exception as e:
    print("❌ Error al conectar con la API de Binance:")
    print(e)
