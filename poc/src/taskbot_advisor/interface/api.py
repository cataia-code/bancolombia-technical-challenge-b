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
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..domain.exceptions import InventoryLoadError
from ..infrastructure.config import Settings
from ..infrastructure.container import build_use_case, write_reports
from ..infrastructure.renderers.json_renderer import JsonRenderer
from ..infrastructure.security import SecurityError, resolve_inventory_path, validate_run_id

app = FastAPI(title="Taskbot Advisor", version="1.0.0")


class AliasedResponse(BaseModel):
    """Response model with English attributes and Spanish wire aliases."""

    model_config = ConfigDict(populate_by_name=True)


class AnalyzeRequest(BaseModel):
    inventory_path: str = Field(..., description="Local path to the inventory (.csv/.json/.sqlite).")
    run_id: str | None = None
    persist: bool = Field(True, description="Write JSON+HTML reports into reports/<run_id>/.")


class InlineRequest(BaseModel):
    taskbots: list[dict] = Field(..., description="Embedded inventory as a list of objects.")
    run_id: str | None = None


class HealthResponse(BaseModel):
    status: str


class DestinationCountsResponse(BaseModel):
    n8n: int
    microservice: int
    custom_python_java: int
    rpa_selective: int
    manual_review: int


class WaveCountsResponse(BaseModel):
    ola_1: int
    ola_2: int
    ola_3: int


class ReviewSummary(AliasedResponse):
    no_review: int = Field(alias="sin_revision")
    ai_precheck: int = Field(alias="prechequeo_ia")
    targeted_approval: int = Field(alias="aprobacion_dirigida")
    manual_deep_dive_strategy: int = Field(alias="evaluacion_manual_profunda")
    governance_gate: int = Field(alias="gate_gobierno")
    ai_assisted: int = Field(alias="asistida_ia")
    manual_deep_dive: int = Field(alias="manual_profunda")


class SummaryResponse(AliasedResponse):
    total_taskbots: int
    consolidation_groups: int = Field(alias="grupos_consolidables")
    by_target: DestinationCountsResponse = Field(alias="por_destino")
    by_wave: WaveCountsResponse = Field(alias="por_ola")
    review: ReviewSummary = Field(alias="revision")
    errors: int = Field(alias="errores")


class SensitivityDeltaResponse(AliasedResponse):
    governance_gate: int = Field(alias="gate_gobierno")
    ai_assisted: int = Field(alias="asistida_ia")
    manual_deep_dive: int = Field(alias="manual_profunda")
    ola_1: int
    ola_2: int
    ola_3: int


class SensitivityBaseResponse(AliasedResponse):
    governance_dependency_threshold: int = Field(alias="umbral_dependencias_gate_gobierno")
    deep_review_complexity_threshold: float = Field(
        alias="umbral_complejidad_manual_profunda"
    )
    review: ReviewSummary = Field(alias="revision")
    by_wave: WaveCountsResponse = Field(alias="por_ola")


class SensitivityScenarioResponse(AliasedResponse):
    governance_dependency_threshold: int = Field(alias="umbral_dependencias_gate_gobierno")
    deep_review_complexity_threshold: float = Field(
        alias="umbral_complejidad_manual_profunda"
    )
    is_base_scenario: bool = Field(alias="escenario_base")
    review: ReviewSummary = Field(alias="revision")
    by_wave: WaveCountsResponse = Field(alias="por_ola")
    delta_vs_base: SensitivityDeltaResponse


class SensitivityResponse(AliasedResponse):
    rule: str = Field(alias="regla")
    base: SensitivityBaseResponse
    scenarios: list[SensitivityScenarioResponse] = Field(alias="escenarios")


class ClusterResponse(AliasedResponse):
    id: int
    members: list[str] = Field(alias="miembros")
    representative: str = Field(alias="representante")
    is_consolidation_group: bool = Field(alias="es_grupo_consolidable")


class ComponentCandidateResponse(AliasedResponse):
    cluster_id: int
    suggested_name: str = Field(alias="nombre_sugerido")
    members: list[str] = Field(alias="miembros")
    names: list[str] = Field(alias="nombres")
    common_purpose: str = Field(alias="proposito_comun")
    target_pattern: str = Field(alias="patron_destino")
    dominant_apps: list[str] = Field(alias="apps_dominantes")
    legacy_blocker: bool = Field(alias="blocker_legacy")
    needs_api_enablement: bool = Field(alias="requiere_habilitacion_api")
    recommended_action: str = Field(alias="accion_recomendada")


class ApiEnablementResponse(AliasedResponse):
    systems: list[str] = Field(alias="sistemas")
    api_available: bool = Field(alias="api_disponible")
    api_required: bool = Field(alias="api_requerida")
    blocker: str | None = Field(alias="bloqueador")
    enabling_action: str = Field(alias="accion_habilitadora")
    target_after_enablement: str = Field(alias="destino_objetivo_post_habilitacion")


class ApiMatrixResponse(AliasedResponse):
    system: str = Field(alias="sistema")
    taskbots: int
    api_available: bool = Field(alias="api_disponible")
    touched_by_legacy: bool = Field(alias="tocado_por_legacy")
    needs_api_enablement: bool = Field(alias="requiere_habilitacion_api")


class EvidencePackResponse(AliasedResponse):
    dependencies: list[str] = Field(alias="dependencias")
    controls: list[str] = Field(alias="controles")
    checklist: list[str]
    suggested_owner: str = Field(alias="owner_sugerido")
    blockers: list[str] = Field(alias="bloqueadores")
    next_action: str = Field(alias="siguiente_accion")


class FrequencyScoreResponse(AliasedResponse):
    bucket: str
    points: float = Field(alias="puntos")


class RiskScoreResponse(AliasedResponse):
    level: str = Field(alias="nivel")
    points: float = Field(alias="puntos")


class DuplicateScoreResponse(AliasedResponse):
    in_group: bool = Field(alias="en_grupo")
    points: float = Field(alias="puntos")


class ValueBreakdownResponse(AliasedResponse):
    frequency: FrequencyScoreResponse = Field(alias="frecuencia")
    risk: RiskScoreResponse = Field(alias="riesgo")
    duplication: DuplicateScoreResponse = Field(alias="duplicidad")
    total: float


class DominantInteractionScoreResponse(AliasedResponse):
    interaction_type: str = Field(alias="tipo")
    points: float = Field(alias="puntos")


class ExtraChannelsScoreResponse(AliasedResponse):
    count: int = Field(alias="cantidad")
    points: float = Field(alias="puntos")


class DependencyScoreResponse(AliasedResponse):
    count: int = Field(alias="cantidad")
    points: float = Field(alias="puntos")


class ComplexityBreakdownResponse(AliasedResponse):
    dominant_interaction: DominantInteractionScoreResponse = Field(alias="interaccion_dominante")
    extra_channels: ExtraChannelsScoreResponse = Field(alias="canales_extra")
    risk: RiskScoreResponse = Field(alias="riesgo")
    dependencies: DependencyScoreResponse = Field(alias="dependencias")
    total: float


class ScoreBreakdownResponse(AliasedResponse):
    value: ValueBreakdownResponse = Field(alias="valor")
    complexity: ComplexityBreakdownResponse = Field(alias="complejidad")


class RecommendationResponse(AliasedResponse):
    taskbot_id: str
    taskbot: str
    target: str = Field(alias="destino")
    ola: str
    value: float = Field(alias="valor")
    complexity: float = Field(alias="complejidad")
    cluster_id: int | None
    manual_review: bool = Field(alias="revision_manual")
    review_type: str = Field(alias="tipo_revision")
    requires_governance_gate: bool = Field(alias="requiere_gate_gobierno")
    ai_assisted_review: bool = Field(alias="revision_asistida_ia")
    review_action: str = Field(alias="accion_revision")
    evidence_pack: EvidencePackResponse
    reasons: list[str] = Field(alias="razones")
    rationale: str = Field(alias="justificacion")
    score_breakdown: ScoreBreakdownResponse
    api_enablement: ApiEnablementResponse | None


class AnalysisResponse(BaseModel):
    run_id: str
    summary: SummaryResponse
    clusters: list[ClusterResponse]
    component_candidates: list[ComponentCandidateResponse]
    api_matrix: list[ApiMatrixResponse]
    sensitivity: SensitivityResponse
    recommendations: list[RecommendationResponse]
    errors: list[dict[str, Any]]


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
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


@app.post("/analyze/inline", response_model=AnalysisResponse)
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
