# `binance-futures`

**Sistema institucional de análisis técnico y contextual para operaciones en Binance Futures (LONG/SHORT) en temporalidades medias y largas.**

Este proyecto está diseñado para analizar el estado del mercado cripto de forma automatizada, detectar oportunidades de inversión de alta probabilidad y reducir el margen de error al mínimo mediante una estructura modular, asincrónica y escalable.

---

## 🧠 Objetivo del sistema

* Operar en Binance Futures en **modo automático o semiautomático**
* Análisis de **contexto institucional completo** antes de evaluar activos (BTC, ETH, DXY, VIX)
* Ejecutar operaciones **solo si el entorno es favorable**
* Soporte para operaciones **LONG y SHORT** diferenciadas
* Escalabilidad hacia múltiples criptomonedas
* Soporte para temporalidades semanales y diarias (no scalping)

---

## 📁 Estructura del proyecto

```
binance-futures/
│
├── main.py                         # Punto de entrada al sistema (orquestador)
├── .env                            # Claves API, configuración sensible
│
├── logic/                          # Lógica principal del análisis
│   ├── market_context.py           # Evalúa BTC, ETH, VIX, DXY, scores de contexto
│   ├── analyzer.py                 # Analiza criptoactivos según contexto
│   ├── reporter.py                 # Exporta CSV/JSON de señales y contexto
│   └── indicators.py               # Cálculo técnico (EMA, RSI, ADX, Volumen, etc.)
│
├── output/                         # Reportes generados por sesión
│   ├── logs/                       # runtime.log, audit.log, errores
│   └── signals.csv                 # Señales evaluadas por día
│
├── utils/                          # Utilidades generales (filtros, funciones comunes)
│   └── telegram.py                 # Notificador (con botones) para decisiones humanas
│
├── config/                         # Parámetros del sistema
│   └── settings.json               # Scores, umbrales, criptos a evaluar
│
└── README.md                       # Documentación principal
```

---

## ⚙️ ¿Qué hace el sistema actualmente?

1. **Evalúa el contexto global**:

   * BTC semanal (EMA, RSI, estructura HL/LH)
   * ETH diario (EMA y momentum)
   * DXY y VIX (para determinar presión externa)
   * Calcula dos scores:

     * `market_score_long`
     * `market_score_short`

2. **Filtra y decide si el mercado es apto para operar**

   * Solo continúa si `score >= 65` para long o short.

3. **(Próximamente)** Analiza múltiples criptomonedas:

   * Detecta setups técnicos con volumen, ruptura, EMAs cruzados, etc.

4. **Registra el análisis completo** en logs y archivos `.csv` para auditoría.

---

## 🛠️ Instalación y ejecución

```bash
# Clona el repositorio
git clone https://github.com/jliobarreto/binance-futures.git
cd binance-futures

# Instala las dependencias
pip install -r requirements.txt

# Crea archivo .env
cp .env.example .env  # y coloca tus claves

# Ejecuta el bot
python main.py
```

---

## 📊 Logs y reportes

* `runtime.log`: ejecución de cada sesión (incluye contexto y errores)
* `audit.log`: decisiones, activos analizados y motivos de rechazo
* `signals.csv`: señales evaluadas y su score completo (por activo)

---

## ✅ Roadmap de desarrollo (fase actual)

| Fase | Componente                                  | Estado       |
| ---- | ------------------------------------------- | ------------ |
| 1    | Análisis de contexto institucional          | ✅ Completo   |
| 2    | Evaluación de BTC y ETH                     | ✅ Activo     |
| 3    | Evaluación múltiple de criptomonedas        | 🔄 En curso  |
| 4    | Sistema de tracking de señales históricas   | 🔜 Pendiente |
| 5    | Generación automática de niveles de entrada | 🔜 Pendiente |
| 6    | Integración con Telegram                    | 🔄 En curso  |
| 7    | Validación por temporalidades mayores       | 🔜 Pendiente |
| 8    | Filtro de volumen y liquidez mínima         | 🔜 Pendiente |

---

## 🤖 Tecnología utilizada

* Python 3.11
* `yfinance` para datos de mercado
* `ta` para indicadores técnicos
* `pandas`, `numpy`, `asyncio` para procesamiento asincrónico
* `logging` avanzado
* Telegram Bot API (próximo)

---

## 👨‍💻 Contacto

Desarrollado por Julio Barreto
Si deseas colaborar o sugerir mejoras, escríbeme directamente.