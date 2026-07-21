"""Part A-compatible discovery facade.

Part A shipped a single ``discovery.py`` module with names such as
``cluster_taskbots``, ``priority_score``, ``api_matrix`` and ``run_discovery``.
Part B keeps the same vocabulary here while delegating to the modular
hexagonal implementation.
"""

from __future__ import annotations

from pathlib import Path

from .domain.api_enablement import system_matrix as api_matrix
from .domain.entities import AnalysisResult, Cluster, Taskbot
from .domain.scoring import complexity_score, value_score
from .domain.similarity import SimilarityFn, build_clusters
from .infrastructure.config import Settings
from .infrastructure.container import build_use_case


def cluster_taskbots(
    bots: list[Taskbot], score_fn: SimilarityFn, threshold: float
) -> list[Cluster]:
    """Part A name for duplicate detection; returns B ``Cluster`` objects."""
    return build_clusters(bots, score_fn, threshold)


def priority_score(bot: Taskbot, in_duplicate_cluster: bool = False) -> float:
    """Rank a taskbot for migration using B's value/complexity scale.

    Part A used a single 1-5 score. Part B keeps value and complexity explicit;
    this facade exposes one bounded number for callers that still expect a
    single priority score.
    """
    value = value_score(bot, in_duplicate_cluster)
    complexity = complexity_score(bot)
    return round(max(0.0, min(100.0, value - (complexity * 0.35))), 1)


def run_discovery(
    inventory_path: str | Path,
    *,
    run_id: str | None = None,
    settings: Settings | None = None,
) -> AnalysisResult:
    """Part A name for the end-to-end local discovery run."""
    return build_use_case(inventory_path, settings or Settings()).execute(run_id=run_id)
