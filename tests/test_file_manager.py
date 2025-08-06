import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.file_manager import append_csv

def test_append_csv_quotes(tmp_path):
    file = tmp_path / "out.csv"
    fila = ["valor1", "valor,con,comas", '"entre"']
    append_csv(fila, file)
    with open(file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        assert next(reader) == fila
