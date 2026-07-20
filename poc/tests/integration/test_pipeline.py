"""Tests de integracion: carga real (.txt/.csv) -> analisis -> reporte."""

from pathlib import Path

import pytest

from taskbot_advisor.domain.entities import MigrationTarget
from taskbot_advisor.infrastructure.config import Settings
from taskbot_advisor.infrastructure.container import build_use_case, write_reports
from taskbot_advisor.infrastructure.renderers.json_renderer import JsonRenderer
from taskbot_advisor.infrastructure.repositories.file_repositories import (
    TxtInventoryRepository,
    repository_for,
)

DATA = Path(__file__).resolve().parents[2] / "data"
TXT = DATA / "ejemplo_50_taskbots_prueba.txt"


def test_txt_repository_carga_50_taskbots():
    bots, errors = TxtInventoryRepository(TXT).load()
    assert len(bots) == 50
    assert errors == []
    # Al menos uno multivaluado (Recepcion de facturas: email/archivo/UI legacy).
    assert any(len(b.known_interactions) >= 3 for b in bots)


def test_factory_reconoce_txt():
    assert isinstance(repository_for(TXT), TxtInventoryRepository)


def test_analisis_end_to_end_produce_todas_las_categorias():
    settings = Settings()  # defaults, sin LLM
    result = build_use_case(TXT, settings).execute(run_id="itest")
    assert result.total == 50
    # El inventario real debe producir variedad de destinos.
    targets = {r.target for r in result.recommendations}
    assert MigrationTarget.RPA_SELECTIVE in targets  # hay UI legacy
    assert MigrationTarget.N8N in targets            # hay API/email/archivo puros
    # Debe detectar grupos consolidables (hay duplicidades declaradas).
    assert len(result.consolidation_groups) >= 1
    assert result.errors == []


def test_write_reports_versiona_por_run_id(tmp_path):
    settings = Settings(reports_dir=str(tmp_path))
    result = build_use_case(TXT, settings).execute(run_id="run_x")
    paths = write_reports(result, settings)
    assert paths["json"].exists() and paths["html"].exists()
    assert (tmp_path / "run_x").is_dir()
    # El JSON es valido y trae el resumen.
    data = JsonRenderer.to_dict(result)
    assert data["summary"]["total_taskbots"] == 50


def test_reproducibilidad_dos_corridas_mismas_decisiones():
    settings = Settings()
    r1 = build_use_case(TXT, settings).execute(run_id="a")
    r2 = build_use_case(TXT, settings).execute(run_id="b")
    d1 = {x.taskbot_id: (x.target, x.wave) for x in r1.recommendations}
    d2 = {x.taskbot_id: (x.target, x.wave) for x in r2.recommendations}
    assert d1 == d2
