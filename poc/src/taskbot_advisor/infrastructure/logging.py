"""Structured JSON logging with a per-run correlation id (Observability).

Each log line is a JSON object: it eases ingestion by any observability
platform and lets you correlate all the processing of a batch through a single
``run_id``.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Formats each record as a JSON line with stable fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach any extra fields (e.g. run_id, taskbot, event).
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(run_id: str, name: str = "taskbot_advisor") -> logging.LoggerAdapter:
    """Return a logger that injects ``run_id`` into every line (traceability)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return _RunIdAdapter(logger, {"run_id": run_id})


class _RunIdAdapter(logging.LoggerAdapter):
    """Attaches run_id (and any extra) to the record as ``extra_fields``."""

    def process(self, msg, kwargs):
        extra = dict(self.extra)
        extra.update(kwargs.pop("extra", {}) or {})
        kwargs["extra"] = {"extra_fields": extra}
        return msg, kwargs
