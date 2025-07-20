# reporter.py

import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

def exportar_resultados_excel(resultados: list[dict], carpeta: str = "output") -> str:
    """
    Exporta los resultados a un archivo Excel ordenado por score.
    """
    if not resultados:
        return ""

    df = pd.DataFrame(resultados).sort_values("Score", ascending=False)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    Path(carpeta).mkdir(parents=True, exist_ok=True)
    archivo = f"{carpeta}/señales_long_short_{timestamp}.xlsx"
    df.to_excel(archivo, index=False)
    return archivo

def exportar_resultados_csv(resultados: list[dict], carpeta: str = "output") -> str:
    """
    Exporta los resultados a un archivo CSV ordenado por score.
    """
    if not resultados:
        return ""

    df = pd.DataFrame(resultados).sort_values("Score", ascending=False)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    Path(carpeta).mkdir(parents=True, exist_ok=True)
    archivo = f"{carpeta}/señales_long_short_{timestamp}.csv"
    df.to_csv(archivo, index=False)
    return archivo

def imprimir_resumen_terminal(resultados: list[dict]) -> None:
    """
    Imprime un resumen de los resultados en consola para validación rápida.
    """
    if not resultados:
        logging.info("No se encontraron oportunidades válidas.")
        return

    logging.info("\n🔍 Resumen de señales generadas:")
    for r in resultados:
        logging.info(
            f"✅ {r['Criptomoneda']} | Tipo: {r['Señal']} | Score: {r['Score']} | Entrada: {r['Precio']:.4f} | TP: {r['TP']:.4f} | SL: {r['SL']:.4f}"
        )

