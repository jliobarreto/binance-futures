Crypto Futures Signal Bot

Este proyecto es un sistema modular y asincrónico diseñado para detectar oportunidades de trading en criptomonedas con un enfoque institucional, minimizando pérdidas y maximizando ganancias. Utiliza indicadores técnicos y análisis matemático sin depender de inteligencia artificial, y está orientado a temporalidades medias y largas.

📂 Estructura de Carpetas

futures_bot/
│
├── main.py                         # Archivo principal que ejecuta todo
├── config.py                       # Configuraciones generales
├── runtime.log                     # Registro de ejecución
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

symbols.py: obtiene los pares USDT válidos y filtra excluidos.

analyzer.py: por cada par:

Consulta datos de precios.

Calcula indicadores.

Evalúa estructura del mercado.

Calcula TP, SL y grids.

filters.py: excluye pares manipulados o con baja liquidez.

scorer.py: asigna una puntuación a cada criptomoneda.

reporter.py: arma mensajes de Telegram y guarda el archivo .xlsx.

notifier.py: envía la señal con botones (Cuenta 1, Cuenta 2, Rechazada).

telegram_webhook.py: (opcional) escucha las respuestas del usuario.

📊 Indicadores Utilizados

RSI (1D y 1W)

MACD y señal

EMAs (20, 50, 200)

Bollinger Bands

ADX

MFI

OBV

ATR (para TP/SL dinámico)

📊 Filtros de Confirmación Obligatorios

Confirmación con temporalidades mayores (multi-frame)

Validación de consolidación previa + ruptura

Validación estructural de TP y SL

Filtro de mercado global (BTC y ETH alcista para LONG)

Exclusión de criptos con volumen descendente o manipulación

📦 Salidas

output/señales_YYYY-MM-DD_HH-MM.xlsx: archivo con resultados de la ejecución

Logs con errores o advertencias si algo falló

Mensajes de Telegram con botones de selección y registro de respuesta en Excel

📅 Futuras Mejoras

Backtesting histórico para validar efectividad de señales

Score mínimo ajustable según contexto de mercado

Detección de eventos de rebote o soporte clave con algorítmica

Integración de Google Sheets o base de datos (PostgreSQL o SQLite)

Mejora en visualización de datos para seguimiento

🚀 Ejecución

python main.py

Requiere definir las siguientes variables de entorno antes de ejecutar:

- `BINANCE_API_KEY` y `BINANCE_API_SECRET` para autenticar en Binance.
- `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` para enviar notificaciones por Telegram.

Estas claves pueden almacenarse en un archivo `.env` en la raíz del proyecto
para evitar exponerlas en el código. El sistema las cargará automáticamente al
ejecutar.

📊 Este proyecto fue diseñado para facilitar decisiones de trading profesional con un enfoque metódico, sin depender de emociones ni de AI compleja. Todo está preparado para analizar en marcos temporales medios y largos, priorizando la seguridad de capital.