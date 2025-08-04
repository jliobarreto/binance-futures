import asyncio
import logging
from binance.client import Client
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    SCORE_THRESHOLD_LONG,
    SCORE_THRESHOLD_SHORT,
    TOP_ANALISIS,
)
from data.symbols import obtener_top_usdt
from logic.analyzer import analizar_simbolo
from logic.market_context import obtener_contexto_mercado
from logic.reporter import (
    exportar_resultados_excel,
    exportar_resultados_csv,
    imprimir_resumen_terminal,
    registrar_signal,
)
from logic.risk_manager import puede_operar
from utils.telegram import enviar_telegram, formatear_senal

def run_bot() -> None:
    """Ejecución principal del sistema."""
    contexto = obtener_contexto_mercado()
    mensaje_tendencia = (
        f"🌐 BTC: {'Alcista ✅' if contexto.btc_alcista else 'Bajista ❌'} | "
        f"ETH: {'Alcista ✅' if contexto.eth_alcista else 'Bajista ❌'} | "
        f"DXY: {'Alza ✅' if contexto.dxy_alcista else 'Baja ❌'} | "
        f"VIX: {contexto.vix_valor:.1f}"
    )
    enviar_telegram(mensaje_tendencia)
    logging.info("Contexto de mercado obtenido")
    logging.info(
        f"Score total: {contexto.score_total:.0f}/100 | "
        f"LONG {contexto.score_long:.0f}/100 | "
        f"SHORT {contexto.score_short:.0f}/100"
    )
    if not contexto.apto_long and not contexto.apto_short:
        logging.info("Mercado desfavorable, análisis detenido")
        enviar_telegram("⚠️ Mercado desfavorable. Trading detenido.")
        return
    if not puede_operar():
        logging.info("Operaciones pausadas por control de riesgo")
        enviar_telegram("⏸ Operaciones pausadas por control de riesgo.")
        return
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logging.error("Faltan credenciales de Binance")
        enviar_telegram("⚠️ Se requieren credenciales de Binance")
        return
    
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    try:
        symbols = obtener_top_usdt(client, limit=TOP_ANALISIS)
    except Exception as e:
        logging.error(f"Error obteniendo símbolos: {e}")
        enviar_telegram("⚠️ Error obteniendo símbolos de Binance")
        return
    logging.info(f"Comenzando análisis de {len(symbols)} símbolos")
    resultados = []
    max_score = None

    logging.info(f"Comenzando análisis de {len(symbols)} símbolos")
    resultados = []
    max_score = None

    for sym in symbols:
        logging.info(f"Analizando {sym}")
        try:
            klines_d = client.get_klines(
                symbol=sym,
                interval=Client.KLINE_INTERVAL_1DAY,
                limit=210,
            )
            klines_w = client.get_klines(
                symbol=sym,
                interval=Client.KLINE_INTERVAL_1WEEK,
                limit=210,
            )
            logging.debug(
                f"{sym} datos diarios: {len(klines_d)} velas, semanales: {len(klines_w)}"
            )
            resultado = analizar_simbolo(
                sym, klines_d, klines_w, contexto.btc_alcista, contexto.eth_alcista
            )
            logging.info(f"Análisis de {sym} completado")
            if resultado:
                tec, score, _factors, _ = resultado
                if tec.tipo == "LONG" and not contexto.apto_long:
                    motivo = (
                        f"Score long {contexto.score_long:.0f}/100 < {SCORE_THRESHOLD_LONG}"
                    )
                    logging.info(f"{sym} descartado – {motivo}")
                    registrar_signal({"symbol": sym, "score": score}, motivo)
                    continue
                if tec.tipo == "SHORT" and not contexto.apto_short:
                    motivo = (
                        f"Score short {contexto.score_short:.0f}/100 < {SCORE_THRESHOLD_SHORT}"
                    )
                    logging.info(f"{sym} descartado – {motivo}")
                    registrar_signal({"symbol": sym, "score": score}, motivo)
                    continue
                if max_score is None or score > max_score:
                    max_score = score
                resultado_dict = {
                    "Criptomoneda": tec.symbol,
                    "Señal": tec.tipo,
                    "Precio": tec.precio,
                    "TP": tec.tp,
                    "SL": tec.sl,
                    "RSI": tec.rsi_1d,
                    "MACD": tec.macd_1d,
                    "MACD_signal": tec.macd_signal_1d,
                    "Vitalidad": tec.volumen_actual / tec.volumen_promedio if tec.volumen_promedio else None,
                    "Grids": tec.grids,
                    "Score": score,
                }
                resultados.append(resultado_dict)
                registrar_signal({"symbol": sym, "score": score})
                logging.info(f"Resultado de {sym}: {resultado_dict}")
                mensaje_senal = formatear_senal(resultado_dict)
                enviar_telegram(mensaje_senal)
            else:
                registrar_signal({"symbol": sym}, "Sin datos")
        except Exception as e:
            logging.error(f"Error analizando {sym}: {e}")
            registrar_signal({"symbol": sym}, f"error: {e}")

    archivo_excel = exportar_resultados_excel(resultados)
    archivo_csv = exportar_resultados_csv(resultados)
    imprimir_resumen_terminal(resultados, len(symbols), max_score)

    if archivo_excel:
        enviar_telegram(f"📊 Reporte Excel generado: {archivo_excel}")
    if archivo_csv:
        enviar_telegram(f"📊 Reporte CSV generado: {archivo_csv}")


__all__ = ["run_bot"]
