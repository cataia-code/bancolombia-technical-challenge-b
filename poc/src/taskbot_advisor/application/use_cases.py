"""Use case: AnalyzeInventory. Orchestrates the domain pipeline.

It is the single coordinator of the flow: load -> clustering -> classification
-> scoring -> wave -> justification. It depends only on ports and the pure
domain; it does not know about concrete CSV, HTTP or LLM (Single Responsibility
+ DIP).
"""

from __future__ import annotations

import uuid

from ..domain import scoring
from ..domain.entities import AnalysisResult, Recommendation
from ..domain.rules import classify_target
from ..domain.similarity import build_clusters, cluster_of
from ..infrastructure.logging import get_logger
from .ports import AgentAdvisor, InventoryRepository, SimilarityScorer


class AnalyzeInventory:
    """Produces migration/consolidation recommendations from the inventory."""

    def __init__(
        self,
        repository: InventoryRepository,
        similarity: SimilarityScorer,
        advisor: AgentAdvisor,
        threshold: float,
    ) -> None:
        self._repository = repository
        self._similarity = similarity
        self._advisor = advisor
        self._threshold = threshold

    def execute(self, run_id: str | None = None) -> AnalysisResult:
        run_id = run_id or uuid.uuid4().hex[:12]
        log = get_logger(run_id)

        bots, load_errors = self._repository.load()
        log.info("inventario_cargado", extra={"cargados": len(bots), "errores": len(load_errors)})

        # Let the similarity engine calibrate global parameters (e.g. "hub" apps)
        # from the whole portfolio, if it exposes the optional 'fit' hook.
        fit = getattr(self._similarity, "fit", None)
        if callable(fit):
            fit(bots)

        # 1. Duplicate detection (clustering by the injected similarity).
        clusters = build_clusters(bots, self._similarity.score, self._threshold)
        log.info(
            "clusters_detectados",
            extra={"clusters": len(clusters),
                   "grupos_consolidables": sum(c.is_duplicate_group for c in clusters)},
        )

        # 2. For each taskbot: classify, score, assign a wave and justify.
        recommendations: list[Recommendation] = []
        errors: list[dict] = list(load_errors)
        for bot in bots:
            try:
                recommendations.append(self._recommend(bot, clusters))
            except Exception as exc:  # Fail-soft: one item must not sink the batch.
                log.error("fallo_taskbot", extra={"taskbot": bot.id}, exc_info=True)
                errors.append({"taskbot_id": bot.id, "error": str(exc)})

        result = AnalysisResult(
            run_id=run_id, recommendations=recommendations, clusters=clusters, errors=errors
        )
        log.info(
            "analisis_completado",
            extra={"total": result.total, "ola_1": len(result.by_wave(scoring.Wave.WAVE_1)),
                   "errores": len(errors)},
        )
        return result

    def _recommend(self, bot, clusters) -> Recommendation:
        cluster = cluster_of(bot.id, clusters)
        in_dup = cluster is not None and cluster.is_duplicate_group

        target, reasons, manual = classify_target(bot, cluster)
        value = scoring.value_score(bot, in_dup)
        complexity = scoring.complexity_score(bot)
        wave = scoring.assign_wave(value, complexity, manual)

        rec = Recommendation(
            taskbot_id=bot.id, taskbot_name=bot.name, target=target, wave=wave,
            value_score=round(value, 1), complexity_score=round(complexity, 1),
            cluster_id=cluster.id if (cluster and cluster.is_duplicate_group) else None,
            reasons=reasons, needs_manual_review=manual,
        )
        # Written justification (deterministic or LLM). Does not alter the decision.
        rec.rationale = self._advisor.explain(bot, rec)
        return rec
