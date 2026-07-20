"""Mapper: converts a raw record (dict) into a Taskbot entity.

Centralizes parsing/normalization so every repository (CSV, JSON, SQLite) shares
exactly the same mapping logic (DRY). It is tolerant of column names in
Spanish/English and of lists expressed as text.
"""

from __future__ import annotations

from ..domain.entities import InteractionType, RiskLevel, Taskbot
from ..domain.exceptions import InvalidTaskbotError

# Accepted column aliases -> canonical field.
_FIELD_ALIASES = {
    "id": {"id", "taskbot_id", "codigo"},
    "name": {"name", "nombre", "taskbot", "nombre_taskbot"},
    "purpose": {"purpose", "proposito", "descripcion", "proposito_funcional"},
    "apps": {"apps", "aplicaciones", "applications", "apps_involucradas"},
    "interaction": {"interaction", "tipo_interaccion", "interaction_type", "tipo"},
    "frequency": {"frequency", "frecuencia", "frecuencia_ejecucion"},
    "risk": {"risk", "riesgo", "riesgo_operacional"},
    "dependencies": {"dependencies", "dependencias", "dependencias_conocidas"},
    "known_similarity": {"known_similarity", "similitud", "duplicidad", "evidencia_duplicidad"},
}


def _pick(record: dict, field: str) -> str:
    """Return the value of the first alias present for ``field`` (or '')."""
    lowered = {str(k).strip().lower(): v for k, v in record.items()}
    for alias in _FIELD_ALIASES[field]:
        if alias in lowered and lowered[alias] is not None:
            return str(lowered[alias]).strip()
    return ""


def _split_list(raw: str) -> tuple[str, ...]:
    """Split a list written as text: accepts ';', ',' or '|' as separator."""
    if not raw:
        return ()
    for sep in (";", "|", ","):
        if sep in raw:
            return tuple(x.strip() for x in raw.split(sep) if x.strip())
    return (raw.strip(),)


def to_taskbot(record: dict) -> Taskbot:
    """Convert a record into a Taskbot. Raises InvalidTaskbotError if invalid."""
    name = _pick(record, "name")
    if not name:
        raise InvalidTaskbotError("Record without a taskbot 'name'.")

    bot_id = _pick(record, "id") or name.lower().replace(" ", "_")
    return Taskbot(
        id=bot_id,
        name=name,
        purpose=_pick(record, "purpose"),
        apps=_split_list(_pick(record, "apps")),
        interactions=InteractionType.parse_many(_pick(record, "interaction")),
        frequency=_pick(record, "frequency"),
        risk=RiskLevel.parse(_pick(record, "risk")),
        dependencies=_split_list(_pick(record, "dependencies")),
        known_similarity=_pick(record, "known_similarity"),
    )
