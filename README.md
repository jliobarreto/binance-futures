Crypto Futures Signal Bot

Este proyecto es un sistema modular y asincrónico diseñado para detectar oportunidades de trading en criptomonedas con un enfoque institucional, minimizando pérdidas y maximizando ganancias. Utiliza indicadores técnicos y análisis matemático sin depender de inteligencia artificial, y está orientado a temporalidades medias y largas.

📂 Estructura de Carpetas

futures_bot/
│
├── main.py                         # Archivo principal que ejecuta todo
├── config.py                       # Configuraciones generales
├── logs/                           # Registro de ejecución
│   └── runtime.log                 # (generado al ejecutar; no forma parte del repo)
├── telegram_webhook.py             # (Opcional) Webhook para respuestas de Telegram
│
├── data/
│   └── symbols.py               # Lista y filtros de criptomonedas
│
├── logic/
│   ├── analyzer.py              # Procesa y arma el contexto técnico
│   ├── filters.py               # Filtros de consolidación, manipulación, volumen
│   ├── indicators.py            # Cálculo de RSI, MACD, ADX, BB, OBV, MFI, etc.
│   ├── scorer.py                # Sistema de puntuación y validación de señales
│   └── reporter.py              # Generador de mensajes y reportes
│
├── utils/
│   ├── telegram.py              # Enviar mensajes y logs a Telegram
│   ├── math_tools.py            # Cálculos matemáticos de soporte
│   └── path.py                  # Rutas automáticas para salida de archivos
│
├── notifier.py                     # Envío de alertas a Telegram con botones
├── output/                         # Archivos generados (.xlsx, logs)
└── README.md                       # Documentación general

📊 Flujo de Ejecución

main.py: orquesta el proceso completo.

@@ -52,27 +53,28 @@ Instale todas las dependencias con:
pip install -r requirements.txt
```


🚀 Ejecución

Antes de correr el bot es necesario configurar las variables de entorno:

- `BINANCE_API_KEY` y `BINANCE_API_SECRET` para autenticar en Binance.
- `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` para enviar notificaciones por Telegram.

Copie el archivo de ejemplo y edite los valores reales con:

```bash
cp .env.example .env
```

Abra `.env` y reemplace con sus credenciales reales. Sin estas
variables el bot no podrá conectarse ni a Binance ni a Telegram.

Finalmente ejecute:

```bash
python main.py
```
Al ejecutarse se creará el archivo `logs/runtime.log` con el registro de la ejecución.

📊 Este proyecto fue diseñado para facilitar decisiones de trading profesional con un enfoque metódico, sin depender de emociones ni de AI compleja. Todo está preparado para analizar en marcos temporales medios y largos, priorizando la seguridad de capital.
