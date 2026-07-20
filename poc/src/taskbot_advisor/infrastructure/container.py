"""Composition root: assembles the use case with its concrete adapters.

A single place where dependencies are resolved, so CLI and API share exactly the
same wiring (DRY) and the rest of the code depends only on abstractions. This is
the only point that knows both domain and infrastructure at once.
"""

from __future__ import annotations

from pathlib import Path

from ..application.use_cases import AnalyzeInventory
from ..domain.entities import AnalysisResult
from .advisor import build_advisor
from .config import Settings
from .renderers.html_renderer import HtmlRenderer
from .renderers.json_renderer import JsonRenderer
from .repositories.file_repositories import repository_for
from .similarity_rapidfuzz import RapidFuzzSimilarity


def build_use_case(inventory_path: str | Path, settings: Settings) -> AnalyzeInventory:
    return AnalyzeInventory(
        repository=repository_for(inventory_path),
        similarity=RapidFuzzSimilarity(settings.apps_overlap_weight),
        advisor=build_advisor(settings),
        threshold=settings.similarity_threshold,
    )


def write_reports(result: AnalysisResult, settings: Settings) -> dict[str, Path]:
    """Write JSON and HTML into reports/<run_id>/ (idempotent, never overwrites other runs).

    Versioning the output by run_id is the basis of the recovery strategy: a
    re-run produces a new folder without destroying previous runs.
    """
    out_dir = Path(settings.reports_dir) / result.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for renderer in (JsonRenderer(), HtmlRenderer()):
        path = out_dir / f"reporte.{renderer.extension}"
        path.write_text(renderer.render(result), encoding="utf-8")
        paths[renderer.extension] = path
    return paths
