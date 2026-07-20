"""Use case: AnalyzeInventory. Orchestrates the domain pipeline.

It is the single coordinator of the flow: load -> clustering -> classification
-> scoring -> wave -> justification. It depends only on ports and the pure
domain; it does not know about concrete CSV, HTTP or LLM (Single Responsibility
+ DIP).
"""

from __future__ import annotations

import uuid

from ..domain import api_enablement, scoring
from ..domain.catalog import build_component_candidates
from ..domain.entities import (
    AnalysisResult,
    Cluster,
    MigrationDecision,
    Recommendation,
    ScoreExplanation,
    Taskbot,
)
from ..domain.rules import classify_target
from ..domain.similarity import build_clusters, cluster_of
from .ports import (
    AgentAdvisor,
    InventoryRepository,
    NullRunLoggerFactory,
    RunLoggerFactory,
    SimilarityScorer,
    TrainableSimilarityScorer,
)


class AnalyzeInventory:
    """Produces migration/consolidation recommendations from the inventory."""

    def __init__(
        self,
        repository: InventoryRepository,
        similarity: SimilarityScorer,
        advisor: AgentAdvisor,
        threshold: float,
        logger_factory: RunLoggerFactory | None = None,
    ) -> None:
        self._repository = repository
        self._similarity = similarity
        self._advisor = advisor
        self._threshold = threshold
        self._logger_factory = logger_factory or NullRunLoggerFactory()

    def execute(self, run_id: str | None = None) -> AnalysisResult:
        run_id = run_id or uuid.uuid4().hex[:12]
        log = self._logger_factory.for_run(run_id)

        bots, load_errors = self._repository.load()
        log.info("inventario_cargado", cargados=len(bots), errores=len(load_errors))

        if isinstance(self._similarity, TrainableSimilarityScorer):
            self._similarity.fit(bots)

        # 1. Duplicate detection (clustering by the injected similarity).
        clusters = build_clusters(bots, self._similarity.score, self._threshold)
        log.info(
            "clusters_detectados",
            clusters=len(clusters),
            grupos_consolidables=sum(c.is_duplicate_group for c in clusters),
        )

        # 2. For each taskbot: classify, score, assign a wave and justify.
        recommendations: list[Recommendation] = []
        errors: list[dict] = list(load_errors)
        processed: list[Taskbot] = []
        for bot in bots:
            try:
                recommendations.append(self._recommend(bot, clusters))
                processed.append(bot)
            except Exception as exc:  # Fail-soft: one item must not sink the batch.
                log.error("fallo_taskbot", taskbot=bot.id, exc_info=True)
                errors.append({"taskbot_id": bot.id, "error": str(exc)})

        # 3. Rationalization plan: reusable-component catalog + API/no-API matrix.
        bots_by_id = {b.id: b for b in processed}
        recs_by_id = {r.taskbot_id: r for r in recommendations}
        component_candidates = build_component_candidates(clusters, bots_by_id, recs_by_id)
        api_matrix = api_enablement.system_matrix(processed)

        result = AnalysisResult(
            run_id=run_id, recommendations=recommendations, clusters=clusters, errors=errors,
            component_candidates=component_candidates, api_matrix=api_matrix,
        )
        log.info(
            "analisis_completado",
            total=result.total,
            ola_1=len(result.by_wave(scoring.Wave.WAVE_1)),
            errores=len(errors),
        )
        return result

    def _recommend(self, bot: Taskbot, clusters: list[Cluster]) -> Recommendation:
        cluster = cluster_of(bot.id, clusters)
        in_dup = cluster is not None and cluster.is_duplicate_group

        target, reasons, manual = classify_target(bot, cluster)
        value = scoring.value_score(bot, in_dup)
        complexity = scoring.complexity_score(bot)
        wave = scoring.assign_wave(value, complexity, manual)

        rec = Recommendation(
            taskbot_id=bot.id,
            taskbot_name=bot.name,
            decision=MigrationDecision(
                target=target,
                wave=wave,
                cluster_id=cluster.id if (cluster and cluster.is_duplicate_group) else None,
                reasons=tuple(reasons),
                needs_manual_review=manual,
            ),
            scores=ScoreExplanation(
                value=round(value, 1),
                complexity=round(complexity, 1),
                breakdown=scoring.score_breakdown(bot, in_dup),
            ),
            api_enablement=api_enablement.assess(bot, target),
        )
        # Written justification (deterministic or LLM). Does not alter the decision.
        rec.rationale = self._advisor.explain(bot, rec)
        return rec
