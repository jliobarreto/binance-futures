# binance-futures

**Sistema institucional de análisis técnico automatizado para operar en Binance Futures a mediano y largo plazo.**  
Utiliza datos del mercado Spot por su mayor precisión y confiabilidad, pero ejecuta operaciones manuales en el mercado de futuros con base en señales altamente filtradas.

---

## 🎯 Objetivo del proyecto

- Analizar el mercado global y técnico para evaluar si operar o no (LONG / SHORT).
- Evaluar todas las criptomonedas que operan con USDT en Binance Spot.
- Aplicar una plantilla institucional de indicadores técnicos para validar señales.
- Notificar señales claras y accionables vía Telegram.
- Registrar y auditar todas las decisiones, incluso las no ejecutadas.

---

## 📌 Características principales

- ✅ **Datos obtenidos desde el mercado Spot** (no Futures).
- ✅ **Análisis técnico modular**: EMA, RSI, volumen, consolidación, ruptura, ATR.
- ✅ **Escaneo completo de todos los pares USDT** con filtro de volumen.
- ✅ **Evaluación de contexto macro (BTC, ETH, VIX, DXY)** para activar o detener análisis.
- ✅ **Notificación vía Telegram con botones de acción** para operar manualmente.
- ✅ **Registro en logs y archivos `.csv` de cada evaluación** para auditoría.
- ✅ **Configuración externa vía archivo `settings.json`**.

---

## 🧠 Estructura del sistema

```

binance-futures/
│
├── main.py                   # Orquestador del flujo principal
├── .env                      # Claves API y configuración sensible
│
├── config/
│   └── settings.json         # Parámetros como score mínimo, volumen mínimo, etc.
│
├── logic/
│   ├── market\_context.py     # Evalúa si el contexto global es apto para operar
│   ├── analyzer.py           # Evalúa cada cripto con la plantilla técnica
│   ├── indicators.py         # Calcula indicadores técnicos y score
│   └── notifier.py           # Envía señales aptas vía Telegram con botones
│
├── output/
│   ├── runtime.log           # Log de ejecución y errores
│   ├── audit.log             # Registro detallado de decisiones
│   └── signals.csv           # Señales técnicas evaluadas
│
└── README.md                 # Este archivo

````

---

## ⚙️ Instalación y uso

```bash
# 1. Clona el repositorio
git clone https://github.com/jliobarreto/binance-futures.git
cd binance-futures

# 2. (Opcional) crea un entorno virtual
python -m venv venv
source venv/bin/activate

# 3. Instala las dependencias
pip install -r requirements.txt
# Incluye módulos como: pandas, numpy, ta, python-binance, openpyxl,
# requests, flask, scipy, python-dotenv y yfinance.

# 4. Configura el archivo .env con tus claves de Binance Spot
cp .env.example .env

# 5. Ejecuta el sistema
python main.py
````

---

## 🧪 Flujo de ejecución

1. **Evaluación de contexto general**

   * BTC (1W), ETH (1D), DXY, VIX
   * Devuelve `market_score_long` y `market_score_short`
   * Solo continúa si alguno ≥ 65

2. **Escaneo de criptos USDT desde mercado Spot**

   * Filtro por volumen diario (ej. mínimo \$5M)
   * Evaluación técnica con indicadores: EMA20/50, RSI, volumen, ruptura, ATR

3. **Clasificación de señales**

   * Score técnico 0–100
   * Marca como `long`, `short` o `descartado`
   * Registra en `signals.csv` y `audit.log`

4. **Notificación vía Telegram**

   * Mensaje por cada señal apta
   * Botones: `✅ Cuenta 1` / `✅ Cuenta 2` / `❌ Rechazar`
   * Guarda resultado de la decisión

---

## 📈 Indicadores técnicos utilizados

| Indicador      | Rol                         |
| -------------- | --------------------------- |
| EMA20 / EMA50  | Tendencia                   |
| RSI            | Momentum                    |
| Volumen        | Validación de ruptura       |
| ATR            | Confirmación de volatilidad |
| Rango 20 velas | Consolidación previa        |

---

## 📤 Resultados esperados

* No opera si el mercado no es apto
* Filtra criptos sin volumen o señales falsas
* Proporciona señales claras y ejecutables
* Registra todo para trazabilidad y mejora futura

---

## 🔐 Seguridad

* Las claves de API y configuración están en el archivo `.env` (no se suben al repositorio)
* Solo se usan datos del mercado Spot (más seguros y completos)
* No se realiza ejecución automática de órdenes

---

## 🧩 Roadmap de mejoras

| Funcionalidad                      | Estado       |
| ---------------------------------- | ------------ |
| Escaneo dinámico de pares USDT     | ✅ Activo     |
| Filtro de volumen y ATR            | ✅ Activo     |
| Plantilla central de indicadores   | ✅ Activo     |
| Registro histórico de señales      | ✅ Activo     |
| Evaluación por score institucional | ✅ Activo     |
| Notificación vía Telegram          | 🔄 En curso  |
| Evaluación posterior de señales    | 🔜 Pendiente |
| Análisis multi-timeframe           | 🔜 Pendiente |

---

## 👨‍💻 Autor

Desarrollado por Julio Barreto
Para consultas, colaboraciones o mejora del proyecto, contáctame directamente.

---
