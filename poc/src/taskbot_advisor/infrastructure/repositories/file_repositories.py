"""Inventory repositories: CSV, JSON, SQLite and the provided TXT catalog.

All satisfy the ``InventoryRepository`` port and share the same mapper
(mapping.to_taskbot). They apply fail-soft: invalid records are accumulated as
errors and do not interrupt loading the rest.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

from ...domain.entities import Taskbot
from ...domain.exceptions import InvalidTaskbotError, InventoryLoadError
from ..mapping import to_taskbot


def _map_records(records: list[dict]) -> tuple[list[Taskbot], list[dict]]:
    bots: list[Taskbot] = []
    errors: list[dict] = []
    for index, record in enumerate(records):
        try:
            bots.append(to_taskbot(record))
        except InvalidTaskbotError as exc:
            errors.append({"row": index, "error": str(exc), "record": record})
    return bots, errors


class CsvInventoryRepository:
    """Reads the inventory from a CSV file (flexible headers)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> tuple[list[Taskbot], list[dict]]:
        if not self._path.exists():
            raise InventoryLoadError(f"CSV file does not exist: {self._path}")
        with self._path.open(newline="", encoding="utf-8-sig") as fh:
            return _map_records(list(csv.DictReader(fh)))


class JsonInventoryRepository:
    """Reads the inventory from JSON: a list of objects or {'taskbots': [...]}."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> tuple[list[Taskbot], list[dict]]:
        if not self._path.exists():
            raise InventoryLoadError(f"JSON file does not exist: {self._path}")
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InventoryLoadError(f"Invalid JSON in {self._path}: {exc}") from exc
        records = data.get("taskbots", []) if isinstance(data, dict) else data
        if not isinstance(records, list):
            raise InventoryLoadError("JSON must be a list or {'taskbots': [...]}.")
        return _map_records(records)


class SqliteInventoryRepository:
    """Reads the inventory from a SQLite table (default 'taskbots')."""

    def __init__(self, path: str | Path, table: str = "taskbots") -> None:
        self._path = Path(path)
        self._table = table

    def load(self) -> tuple[list[Taskbot], list[dict]]:
        if not self._path.exists():
            raise InventoryLoadError(f"SQLite database does not exist: {self._path}")
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(f"SELECT * FROM {self._table}").fetchall()
        except sqlite3.OperationalError as exc:
            raise InventoryLoadError(f"Could not read table {self._table}: {exc}") from exc
        finally:
            conn.close()
        return _map_records([dict(r) for r in rows])


class TxtInventoryRepository:
    """Reads the catalog in the block format of the provided sample file.

    Format (blocks separated by lines of '='):
        Taskbot NN
        Nombre del taskbot: ...
        Proposito funcional: ...
        Aplicaciones involucradas: A, B, C
        Tipo de interaccion: email, archivo, UI legacy
        Frecuencia de ejecucion: ...
        Riesgo operacional: Medio
        Dependencias conocidas: ...
        Evidencia de duplicidad o similitud con otros taskbots: ...
    """

    # File label -> canonical mapper field.
    _LABELS = {
        "nombre del taskbot": "nombre",
        "proposito funcional": "proposito",
        "aplicaciones involucradas": "aplicaciones",
        "tipo de interaccion": "tipo_interaccion",
        "frecuencia de ejecucion": "frecuencia",
        "riesgo operacional": "riesgo",
        "dependencias conocidas": "dependencias",
        "evidencia de duplicidad o similitud con otros taskbots": "evidencia_duplicidad",
    }

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> tuple[list[Taskbot], list[dict]]:
        if not self._path.exists():
            raise InventoryLoadError(f"TXT file does not exist: {self._path}")
        text = self._path.read_text(encoding="utf-8")
        records: list[dict] = []
        for raw_block in re.split(r"={5,}", text):
            record = self._parse_block(raw_block)
            if record:
                records.append(record)
        if not records:
            raise InventoryLoadError(f"No taskbots recognized in {self._path}")
        return _map_records(records)

    def _parse_block(self, block: str) -> dict | None:
        record: dict = {}
        current_id = None
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^Taskbot\s+(\w+)", line, flags=re.IGNORECASE)
            if m:
                current_id = f"TB{m.group(1)}"
                continue
            if ":" in line:
                label, _, value = line.partition(":")
                field = self._LABELS.get(label.strip().lower())
                if field:
                    record[field] = value.strip()
        if "nombre" not in record:
            return None
        record.setdefault("id", current_id or record["nombre"])
        return record


def repository_for(path: str | Path):
    """Factory: picks the repository based on the file extension."""
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return CsvInventoryRepository(path)
    if suffix == ".json":
        return JsonInventoryRepository(path)
    if suffix in (".sqlite", ".db", ".sqlite3"):
        return SqliteInventoryRepository(path)
    if suffix == ".txt":
        return TxtInventoryRepository(path)
    raise InventoryLoadError(f"Unsupported inventory extension: {suffix!r}")
