"""HTTP API (FastAPI) exposing the analysis so n8n can orchestrate it.

Endpoints:
  GET  /health              -> readiness for n8n / docker healthcheck.
  POST /analyze             -> analyze the inventory (given path) and return JSON.
  POST /analyze/inline      -> analyze an inventory sent in the body (no file).

The API is a thin interface adapter: it validates input and delegates to the use
case.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..domain.exceptions import InventoryLoadError
from ..infrastructure.config import Settings
from ..infrastructure.container import build_use_case, write_reports
from ..infrastructure.renderers.json_renderer import JsonRenderer
from ..infrastructure.security import SecurityError, resolve_inventory_path, validate_run_id

app = FastAPI(title="Taskbot Advisor", version="1.0.0")


class AnalyzeRequest(BaseModel):
    inventory_path: str = Field(..., description="Local path to the inventory (.csv/.json/.sqlite).")
    run_id: str | None = None
    persist: bool = Field(True, description="Write JSON+HTML reports into reports/<run_id>/.")


class InlineRequest(BaseModel):
    taskbots: list[dict] = Field(..., description="Embedded inventory as a list of objects.")
    run_id: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    settings = Settings.from_env()
    # Guardrails: validate run_id and contain the inventory path (defense in depth).
    try:
        run_id = validate_run_id(req.run_id)
        inventory_path = resolve_inventory_path(req.inventory_path, settings.inventory_root)
    except SecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        result = build_use_case(inventory_path, settings).execute(run_id=run_id)
    except InventoryLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.persist:
        write_reports(result, settings)
    return JsonRenderer.to_dict(result)


@app.post("/analyze/inline")
def analyze_inline(req: InlineRequest) -> dict:
    """Analyze an inventory sent in the body (useful for n8n without files)."""
    import json

    settings = Settings.from_env()
    try:
        run_id = validate_run_id(req.run_id)
    except SecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump({"taskbots": req.taskbots}, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    try:
        result = build_use_case(tmp_path, settings).execute(run_id=run_id)
    finally:
        tmp_path.unlink(missing_ok=True)
    return JsonRenderer.to_dict(result)
