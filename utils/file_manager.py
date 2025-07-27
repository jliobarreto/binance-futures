from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def append_csv(row: Iterable[str], file_path: str | Path) -> None:
    """Append a row to a CSV file creating it if needed."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(list(row))
