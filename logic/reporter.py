# reporter.py

import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from utils.file_manager import append_csv
from utils.path import LOGS_DIR

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
    ruta = str(Path(archivo).resolve())
    logging.info(f"Archivo Excel exportado en {ruta}")
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
    ruta = str(Path(archivo).resolve())
    logging.info(f"Archivo CSV exportado en {ruta}")
    return archivo

def imprimir_resumen_terminal(
    resultados: list[dict], evaluados: int | None = None, score_max: float | None = None
) -> None:
    """Imprime un resumen de los resultados en consola para validación rápida.

    Cuando no se encuentran oportunidades válidas también se informa cuántos
    símbolos fueron evaluados y, de proporcionarse, el score máximo obtenido.
    """
    if not resultados:
        mensaje = "No se encontraron oportunidades válidas."
        if evaluados is not None:
            mensaje += f" Se evaluaron {evaluados} símbolos."
        if score_max is not None:
            mensaje += f" Score máximo observado: {score_max:.2f}."
        logging.info(mensaje)
        return

    logging.info("\n🔍 Resumen de señales generadas:")
    for r in resultados:
        logging.info(
            f"✅ {r['Criptomoneda']} | Tipo: {r['Señal']} | Score: {r['Score']} | Entrada: {r['Precio']:.4f} | TP: {r['TP']:.4f} | SL: {r['SL']:.4f}"
        )

def registrar_contexto_csv(datos: dict, archivo: str | Path = LOGS_DIR / "context_summary.csv") -> str:
    """Guarda un resumen del contexto de mercado en un CSV."""
    path = Path(archivo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        append_csv(list(datos.keys()), path)
    append_csv([str(datos[k]) for k in datos.keys()], path)
    ruta = str(path.resolve())
    logging.info(f"Contexto macro registrado en {ruta}")
    return ruta
