# Binance Futures Institutional Bot

Este proyecto es un sistema de análisis y ejecución automatizada de operaciones en Binance Futures, con enfoque institucional y diseñado para estrategias de **mediano y largo plazo** (desde días hasta varios meses por operación). Está orientado a **maximizar la rentabilidad con base en datos reales del mercado**, manteniendo una gestión de riesgo estricta y reinvirtiendo de forma compuesta los beneficios generados.

La arquitectura del sistema es modular, escalable, y separa claramente la lógica de análisis, evaluación, ejecución, gestión de riesgo y seguimiento de resultados.

---

## Objetivo general

Construir un bot institucional de trading para Binance Futures que:

1. Analice de forma autónoma la salud del mercado global (BTC, ETH, SPY, DXY, VIX).
2. Detecte estructuras de consolidación y rupturas válidas con volumen real.
3. Ejecute operaciones **long o short** únicamente cuando se cumplan condiciones estrictas.
4. Asigne una puntuación objetiva a cada activo antes de operar (sistema de score institucional).
5. Mantenga control de riesgo y drawdown con reglas automáticas.
6. Notifique en tiempo real las oportunidades por Telegram con botones interactivos.
7. Registre de forma estructurada cada operación y proyecte crecimiento de capital con interés compuesto.

---

## Alcance operativo

- Tipo de trading: Futures
- Plataforma: Binance (API oficial)
- Temporalidad: Diario y Semanal
- Operativa: Position Trading (no intradía, no scalping)
- Control de riesgo: dinámico, estructural, max 3% por operación
- Reinversión: 100% mensual del capital generado

---

## Tecnologías y dependencias

- Python 3.10 o superior
- [TA-Lib](https://mrjbq7.github.io/ta-lib/) – Indicadores técnicos
- [pandas](https://pandas.pydata.org/) – Manipulación de series temporales
- [numpy](https://numpy.org/) – Cálculo numérico
- [yfinance](https://pypi.org/project/yfinance/) – Datos macro de BTC, ETH, SPY, DXY, etc.
- [Binance API](https://binance-docs.github.io/apidocs/) – Spot y Futures
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) – Notificaciones con botones
- [dotenv](https://pypi.org/project/python-dotenv/) – Gestión de claves y configuración segura

---

## Estructura de carpetas y archivos

```bash
binance-futures/
│
├── main.py                       # Ejecución principal: análisis, filtro de mercado, scoring y notificación
├── config.py                     # Variables globales del sistema (riesgo, umbrales, tokens)
├── .env                          # Claves privadas y configuración segura (excluido del repo)
│
├── /logic/                       # Lógica principal del sistema
│   ├── analyzer.py               # Reglas de análisis técnico multi-frame
│   ├── scorer.py                 # Algoritmo de puntuación institucional por activo
│   ├── structure_validator.py    # Detección de consolidación + ruptura confirmada
│   ├── market_filter.py          # Filtro de salud del mercado (BTC, ETH, DXY, VIX)
│   └── risk_manager.py           # (opcional) Gestión dinámica de SL y TP
│
├── /indicators/                  # Indicadores técnicos calculados desde TA-Lib y personalizados
│   └── indicators.py             # RSI, ADX, MFI, OBV, Bollinger Bands, etc.
│
├── /utils/                       # Funciones auxiliares reutilizables
│   ├── telegram_utils.py         # Lógica de botones, manejo de respuestas, formateo de mensajes
│   ├── data_loader.py            # Descarga y limpieza de datos
│   └── file_manager.py           # Lectura y escritura de logs, Excel, seguimiento de señales
│
├── /data/                        # Datos locales, logs, resultados
│   ├── logs/                     # Historial de errores y ejecuciones
│   ├── signals/                  # Señales generadas por fecha
│   └── capital_tracker.xlsx      # Archivo que registra evolución del capital (interés compuesto)
│
├── /output/                      # Resultados exportados: operaciones ejecutadas, backtests, gráficas
│
├── /notifier/                    # Módulo de notificación a Telegram
│   └── notifier.py               # Envía señales con botones: Cuenta 1, Cuenta 2, Rechazada
│
├── /assets/                      # Documentación, plantillas, imágenes de arquitectura (si aplica)
│
└── README.md                     # Documento principal del repositorio
````

---

## Flujo lógico de ejecución (resumen)

1. **`main.py`** inicia el proceso: carga símbolos, configura variables, invoca el filtro de mercado.
2. Si el mercado es saludable:

   * Se analiza cada símbolo con `analyzer.py` y `structure_validator.py`.
   * Se asigna puntuación mediante `scorer.py`.
   * Si supera el umbral, se notifica vía Telegram con `notifier.py`.
3. Se guarda en `data/signals/` la señal generada con su score y condición estructural.
4. El usuario aprueba la operación desde Telegram (Cuenta 1 o Cuenta 2).
5. Se ejecuta (fase futura) y se registra el resultado en `capital_tracker.xlsx`.

---

## Parámetros clave en `config.py`

* `risk_per_trade`: Porcentaje del capital total a arriesgar por operación
* `min_score_threshold`: Puntuación mínima para enviar señal
* `rsi_threshold_btc`: RSI mínimo de BTC para considerar el mercado saludable
* `long_signal_conditions`: Diccionario de reglas específicas para posiciones long
* `short_signal_conditions`: Reglas específicas para short
* `telegram_token`, `telegram_chat_id`: Claves de autenticación para el bot

---

## Estado actual del desarrollo

| Módulo                   | Estado        | Observaciones                                                       |
| ------------------------ | ------------- | ------------------------------------------------------------------- |
| `main.py`                | Implementado  | Funciona como orquestador general                                   |
| `market_filter.py`       | Listo         | Evalúa salud de BTC y ETH (RSI, MA50)                               |
| `structure_validator.py` | En desarrollo | Requiere detección de consolidaciones y rupturas confirmadas        |
| `scorer.py`              | Parcial       | Requiere agregar factores como volumen, estructura, salud BTC, etc. |
| `notifier.py`            | Listo         | Envío de señal con botones interactivos a Telegram                  |
| `tracker.py`             | Planificado   | Deberá calcular capital mensual, drawdown y curva de crecimiento    |

---

## Siguientes pasos recomendados

1. Completar `structure_validator.py` para validar estructuras macro (semanal + diario).
2. Separar claramente la lógica de entradas **long** y **short**.
3. Enriquecer `scorer.py` con:

   * Confirmación multi-frame
   * Volumen relativo
   * Divergencias (RSI, OBV, MFI)
   * Puntos estructurales (pullback, retesteo)
4. Crear `tracker.py` para:

   * Calcular la evolución mensual del capital
   * Registrar drawdown y profit mensual
   * Mostrar proyección del interés compuesto
5. Integrar validación de calendario macroeconómico (opcional)

---

## Seguridad

* Las claves API están en el archivo `.env`, y deben protegerse. No se suben al repositorio.
* Las API de Binance deben tener permisos restringidos (sin retiros).
* Se recomienda usar entorno virtual y autenticación por IP para producción.

---

## Documentación adicional

* Guía de despliegue en servidor (próxima versión)
* Manual técnico de configuración (en progreso)
* Registro histórico de señales y resultados (en tracker)

---

## Contacto técnico

* Autor y líder del proyecto: Julio Barreto
* Repositorio oficial: [https://github.com/jliobarreto/binance-futures](https://github.com/jliobarreto/binance-futures)
