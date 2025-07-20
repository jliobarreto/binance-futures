# Binance Futures Institutional Bot

Este proyecto tiene como objetivo el desarrollo de un sistema automatizado de análisis y ejecución de operaciones en Binance Futures, orientado a estrategias de mediano y largo plazo (operaciones que se mantienen durante semanas o meses), con un enfoque institucional y un fuerte control de riesgo. Está diseñado para lograr un crecimiento sostenido del capital a través de reinversión y toma de decisiones basadas en datos estructurales del mercado.

---

## Objetivos generales

- Automatizar el análisis técnico multi-temporal de activos en Binance Futures.
- Filtrar oportunidades únicamente cuando las condiciones del mercado sean saludables.
- Validar estructuras técnicas confiables (consolidaciones y rupturas confirmadas).
- Ejecutar operaciones long y short en función de condiciones específicas y diferenciadas.
- Controlar el riesgo por operación y registrar resultados con fines de retroalimentación.
- Escalar progresivamente el capital mediante reinversión compuesta.
- Integrar funcionalidades de notificación y control vía Telegram.

---

## Arquitectura del sistema

El sistema está organizado de manera modular para facilitar la escalabilidad, el mantenimiento y la integración de nuevos componentes.

### Estructura actual de módulos

| Módulo                | Descripción                                                                                 |
|-----------------------|---------------------------------------------------------------------------------------------|
| `main.py`             | Ejecuta el flujo principal del bot: evaluación del mercado, análisis de activos y notificación. |
| `config.py`           | Contiene parámetros globales de configuración: API keys, riesgo por operación, umbrales, etc. |
| `symbols.py`          | Define la lista de símbolos (activos) a analizar. Puede incluir filtros personalizados.     |
| `indicators.py`       | Calcula indicadores técnicos como RSI, ADX, OBV, MFI, Bollinger Bands, entre otros.         |
| `analyzer.py`         | Aplica reglas de análisis técnico estructurado por activo.                                  |
| `scorer.py`           | Asigna una puntuación por activo, basada en múltiples criterios técnicos, estructurales y de volumen. |
| `notifier.py`         | Envía señales al canal de Telegram con botones interactivos (Cuenta 1, Cuenta 2, Rechazada). |
| `utils/`              | Contiene funciones auxiliares compartidas entre los distintos módulos.                      |
| `market_filter.py`    | Evalúa la salud del mercado global (BTC, ETH, DXY) y bloquea operaciones si las condiciones no son favorables. |
| `structure_validator.py` | Detecta estructuras limpias de consolidación + ruptura con volumen. En desarrollo.          |
| `tracker.py`          | Proyectará la evolución del capital con reinversión, registro de drawdowns y rentabilidad. En planificación. |

---

## Estrategia de trading institucional

El sistema está diseñado bajo los principios del trading institucional, priorizando el análisis estructural del mercado y la operativa únicamente en escenarios de alta probabilidad.

### Fundamentos clave

1. **Temporalidad operativa**: diario y semanal.
2. **Tipo de operaciones**: posición (position trading), tanto long como short, con criterios independientes.
3. **Condiciones obligatorias para operar**:
   - Tendencia saludable en BTC y ETH.
   - Consolidación previa con ruptura válida.
   - Volumen creciente en la ruptura.
   - Confirmación con indicadores técnicos estructurales (RSI, OBV, MFI, ADX).
   - Confirmación en múltiples temporalidades (diaria y semanal).
4. **Riesgo por operación**: configurable (por defecto 3 % del capital).
5. **Gestión del capital**: reinversión mensual del 100 % de las ganancias.
6. **Control de pérdidas**:
   - Pausa automática del sistema tras dos operaciones consecutivas perdedoras.
   - Bloqueo de operaciones si el mercado presenta manipulación o alta volatilidad sin contexto estructurado.

---

## Flujo operativo

1. Verificación de condiciones del mercado global (`market_filter.py`).
2. Análisis estructural por activo (`analyzer.py` + `structure_validator.py`).
3. Cálculo del score institucional (`scorer.py`).
4. Evaluación de oportunidades long o short según lógica diferenciada.
5. Envío de señales a Telegram con botones de confirmación.
6. Registro de resultados para retroalimentación futura (`tracker.py`).

---

## Integraciones y dependencias

- **Binance API**: para análisis de precios y ejecución de operaciones (Futures).
- **Yahoo Finance (yfinance)**: para análisis macro de BTC, ETH, DXY y SPY.
- **TA-Lib / Pandas / NumPy**: para cálculos técnicos y manipulación de datos.
- **Telegram Bot API**: para notificaciones de señales y control humano supervisado.
- **XlsxWriter (o similar)**: para registro local de operaciones y rendimiento (en `tracker.py`).

---

## Casos de ejemplo

### Caso 1: Activación de señal long

- BTC presenta estructura saludable (Higher Low confirmado en gráfico diario).
- El activo ADA rompe una consolidación semanal con volumen creciente.
- RSI > 50, OBV ascendente, MFI validando acumulación institucional.
- `scorer.py` otorga 88.2 % de score institucional.
- Se envía señal con entrada y SL estructural definido.
- Resultado: operación mantenida 14 días, TP2 alcanzado, retorno del 9 %.

---

## Roadmap de desarrollo

| Etapa                        | Estado       | Descripción                                                                      |
|-----------------------------|--------------|----------------------------------------------------------------------------------|
| Implementación de market_filter | Completo     | Bloquea operaciones si BTC/ETH no presentan condiciones saludables.             |
| Estructura de análisis técnico | En desarrollo | Validación de ruptura y retesteo en múltiples temporalidades.                   |
| Separación lógica long/short  | Pendiente    | Diferenciación de reglas técnicas y estructurales por dirección de operación.   |
| Registro de evolución de capital | Planificado  | Módulo `tracker.py` para proyección de crecimiento por interés compuesto.       |
| Backtesting segmentado        | Planificado  | Evaluación de efectividad en diferentes escenarios de mercado.                  |
| Evaluador de drawdown         | Planificado  | Registro de pérdidas mensuales y activación de protocolos de control.           |

---

## Requisitos técnicos

- Python 3.10+
- TA-Lib
- yFinance
- NumPy
- Pandas
- Python-Telegram-Bot
- requests
- dotenv

---

## Seguridad

- Las credenciales de acceso (API key, secret) deben almacenarse en un archivo `.env`, que no debe ser compartido ni subido al repositorio.
- No se habilitan permisos de retiro en las API Keys. Solo lectura y trading.
- Se recomienda el uso de IP restringida para operar en entorno real.
