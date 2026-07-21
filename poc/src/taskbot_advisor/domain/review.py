"""Governance review policy for migration recommendations.

This module keeps risk governance separate from the technology-target rules.
The output distinguishes a true manual deep dive from AI-assisted preparation,
so high-risk work is controlled without inflating the manual evaluation queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .entities import (
    Cluster,
    EvidencePack,
    InteractionType,
    MigrationTarget,
    ReviewPlan,
    ReviewStrategy,
    RiskLevel,
    Taskbot,
    Wave,
)
from .scoring import assign_wave

# High-risk taskbots with several dependencies need a governance gate.
GOVERNANCE_DEPENDENCY_THRESHOLD = 3
# Above this value the item is hard enough to require deep manual assessment.
DEEP_REVIEW_COMPLEXITY_MIN = 85.0
SENSITIVITY_COMPLEXITY_THRESHOLDS = (80.0, DEEP_REVIEW_COMPLEXITY_MIN, 90.0)
SENSITIVITY_DEPENDENCY_THRESHOLDS = (GOVERNANCE_DEPENDENCY_THRESHOLD, 4)


@dataclass(frozen=True)
class ReviewSensitivityInput:
    """Minimal per-taskbot data needed to recalculate review/wave thresholds."""

    bot: Taskbot
    cluster: Cluster | None
    target: MigrationTarget
    value: float
    complexity: float


def assess_review(
    bot: Taskbot,
    cluster: Cluster | None,
    target: MigrationTarget,
    complexity: float,
    *,
    governance_dependency_threshold: int = GOVERNANCE_DEPENDENCY_THRESHOLD,
    deep_review_complexity_min: float = DEEP_REVIEW_COMPLEXITY_MIN,
) -> ReviewPlan:
    """Classify the review effort required before implementation."""
    base_pack = _build_evidence_pack(bot, cluster, target)
    if target is MigrationTarget.MANUAL_REVIEW or not bot.known_interactions:
        action = "Levantar la via real de integracion antes de decidir destino u ola."
        return ReviewPlan(
            strategy=ReviewStrategy.MANUAL_DEEP_DIVE,
            reason="Tipo de interaccion no reconocido: requiere evaluacion humana.",
            action=action,
            evidence_pack=_with_next_action(base_pack, action),
        )

    dependency_count = len(bot.dependencies)
    if bot.risk is not RiskLevel.HIGH or dependency_count < governance_dependency_threshold:
        return ReviewPlan(evidence_pack=_with_next_action(base_pack, "Sin accion adicional."))

    base_reason = f"Alto riesgo operacional con {dependency_count} dependencias."
    if complexity > deep_review_complexity_min:
        action = (
            "Arquitectura y operacion deben decidir redisenio, API enablement "
            "o permanencia temporal en RPA antes de ejecutar."
        )
        return ReviewPlan(
            strategy=ReviewStrategy.MANUAL_DEEP_DIVE,
            reason=f"{base_reason} Complejidad extrema: requiere evaluacion manual profunda.",
            action=action,
            evidence_pack=_with_next_action(base_pack, action),
        )

    has_repeatable_pattern = cluster is not None and cluster.is_duplicate_group
    if bot.has(InteractionType.API) or has_repeatable_pattern:
        action = (
            "Generar evidence pack con IA: dependencias, controles, excepciones, "
            "datos de prueba y checklist de aprobacion."
        )
        return ReviewPlan(
            strategy=ReviewStrategy.AI_PRECHECK,
            reason=(
                f"{base_reason} Existe API o patron repetible: resolver con "
                "prechequeo asistido por IA, no con evaluacion manual completa."
            ),
            action=action,
            evidence_pack=_with_next_action(base_pack, action),
        )

    action = (
        "IA prepara checklist y mapa de dependencias; arquitectura valida solo "
        "el bloqueo legacy/API antes de implementar."
    )
    return ReviewPlan(
        strategy=ReviewStrategy.TARGETED_APPROVAL,
        reason=(
            f"{base_reason} Complejidad controlada, pero sin API/patron repetible "
            "para automatizar todo el gate."
        ),
        action=action,
        evidence_pack=_with_next_action(base_pack, action),
    )


def build_review_sensitivity(
    items: Iterable[ReviewSensitivityInput],
    *,
    complexity_thresholds: Iterable[float] = SENSITIVITY_COMPLEXITY_THRESHOLDS,
    dependency_thresholds: Iterable[int] = SENSITIVITY_DEPENDENCY_THRESHOLDS,
) -> dict[str, object]:
    """Recalculate review/wave counts across bounded threshold scenarios."""
    rows = list(items)
    complexity_values = _unique_sorted_float(complexity_thresholds)
    dependency_values = _unique_sorted_int(dependency_thresholds)
    base_counts = _scenario_counts(
        rows,
        deep_review_complexity_min=DEEP_REVIEW_COMPLEXITY_MIN,
        governance_dependency_threshold=GOVERNANCE_DEPENDENCY_THRESHOLD,
    )
    scenarios = []
    for dependency_threshold in dependency_values:
        for complexity_threshold in complexity_values:
            counts = _scenario_counts(
                rows,
                deep_review_complexity_min=complexity_threshold,
                governance_dependency_threshold=dependency_threshold,
            )
            scenarios.append(
                {
                    "umbral_dependencias_gate_gobierno": dependency_threshold,
                    "umbral_complejidad_manual_profunda": complexity_threshold,
                    "escenario_base": (
                        dependency_threshold == GOVERNANCE_DEPENDENCY_THRESHOLD
                        and complexity_threshold == DEEP_REVIEW_COMPLEXITY_MIN
                    ),
                    "revision": counts["revision"],
                    "por_ola": counts["por_ola"],
                    "delta_vs_base": _delta(counts, base_counts),
                }
            )
    return {
        "regla": (
            "Gate de gobierno si riesgo=high y dependencias >= umbral; "
            "manual profunda si complejidad > umbral."
        ),
        "base": {
            "umbral_dependencias_gate_gobierno": GOVERNANCE_DEPENDENCY_THRESHOLD,
            "umbral_complejidad_manual_profunda": DEEP_REVIEW_COMPLEXITY_MIN,
            "revision": base_counts["revision"],
            "por_ola": base_counts["por_ola"],
        },
        "escenarios": scenarios,
    }


def _scenario_counts(
    items: list[ReviewSensitivityInput],
    *,
    deep_review_complexity_min: float,
    governance_dependency_threshold: int,
) -> dict[str, dict[str, int]]:
    review_counts = {strategy.value: 0 for strategy in ReviewStrategy}
    wave_counts = {wave.value: 0 for wave in Wave}
    for item in items:
        review = assess_review(
            item.bot,
            item.cluster,
            item.target,
            item.complexity,
            governance_dependency_threshold=governance_dependency_threshold,
            deep_review_complexity_min=deep_review_complexity_min,
        )
        review_counts[review.strategy.value] += 1
        wave = assign_wave(item.value, item.complexity, review.requires_governance_gate)
        wave_counts[wave.value] += 1

    revision = {
        **review_counts,
        "gate_gobierno": sum(
            review_counts[strategy.value]
            for strategy in ReviewStrategy
            if strategy is not ReviewStrategy.NONE
        ),
        "asistida_ia": (
            review_counts[ReviewStrategy.AI_PRECHECK.value]
            + review_counts[ReviewStrategy.TARGETED_APPROVAL.value]
        ),
        "manual_profunda": review_counts[ReviewStrategy.MANUAL_DEEP_DIVE.value],
    }
    return {"revision": revision, "por_ola": wave_counts}


def _delta(current: dict[str, dict[str, int]], base: dict[str, dict[str, int]]) -> dict[str, int]:
    keys = ("gate_gobierno", "asistida_ia", "manual_profunda")
    revision_delta = {
        key: current["revision"][key] - base["revision"][key]
        for key in keys
    }
    wave_delta = {
        key: current["por_ola"][key] - base["por_ola"][key]
        for key in ("ola_1", "ola_2", "ola_3")
    }
    return {**revision_delta, **wave_delta}


def _unique_sorted_float(values: Iterable[float]) -> tuple[float, ...]:
    return tuple(sorted({float(value) for value in values}))


def _unique_sorted_int(values: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted({int(value) for value in values}))


def _build_evidence_pack(
    bot: Taskbot,
    cluster: Cluster | None,
    target: MigrationTarget,
) -> EvidencePack:
    controls = ["validar impacto operacional", "confirmar rollback y monitoreo"]
    checklist = [
        "verificar dependencias declaradas",
        "preparar datos de prueba",
        "validar responsable de aprobacion",
    ]
    blockers: list[str] = []
    if bot.has(InteractionType.UI_LEGACY):
        blockers.append("ui_legacy")
        checklist.append("validar alternativa API para UI legacy")
    if bot.has(InteractionType.DATABASE):
        controls.append("validar consistencia transaccional")
    if cluster is not None and cluster.is_duplicate_group:
        controls.append(f"comparar variantes del cluster {cluster.id}")
        checklist.append("definir flujo canonico para retirar duplicados")
    owner = "arquitectura"
    if target is MigrationTarget.RPA_SELECTIVE:
        owner = "arquitectura + operacion RPA"
    elif target is MigrationTarget.N8N:
        owner = "equipo integracion/n8n"
    elif target is MigrationTarget.CUSTOM_PYTHON_JAVA:
        owner = "equipo backend"
    elif target is MigrationTarget.MICROSERVICE:
        owner = "equipo plataforma"
    return EvidencePack(
        dependencies=bot.dependencies,
        controls=tuple(controls),
        checklist=tuple(checklist),
        suggested_owner=owner,
        blockers=tuple(blockers),
    )


def _with_next_action(pack: EvidencePack, next_action: str) -> EvidencePack:
    return EvidencePack(
        dependencies=pack.dependencies,
        controls=pack.controls,
        checklist=pack.checklist,
        suggested_owner=pack.suggested_owner,
        blockers=pack.blockers,
        next_action=next_action,
    )
