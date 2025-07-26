from pathlib import Path
import csv
from logic.reporter import registrar_contexto_csv

def test_registrar_contexto_csv(tmp_path):
    datos = {"fecha": "2024-01-01T00:00:00", "score_long": "80", "score_short": "20"}
    archivo = tmp_path / "ctx.csv"
    ruta = registrar_contexto_csv(datos, archivo)
    assert Path(ruta).is_file()
    with open(ruta, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == list(datos.keys())
    assert rows[1] == list(datos.values())
