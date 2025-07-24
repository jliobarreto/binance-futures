"""Funciones sencillas para manejar archivos locales."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import csv


def guardar_json(data: Any, path: str | Path) -> None:
    """Guarda ``data`` en un archivo JSON."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def leer_json(path: str | Path) -> Any:
    """Lee un archivo JSON y retorna su contenido."""
    if not Path(path).is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def append_csv(fila: list[str], path: str | Path) -> None:
    """Agrega una fila a un CSV, creando el archivo si no existe."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    modo = "a" if Path(path).exists() else "w"
    with open(path, modo, encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fila)
