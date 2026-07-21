"""Deterministic rules for classifying the technology target.

This is the core business criterion: given a taskbot (with possibly SEVERAL
interaction types) and its cluster membership, it decides which migration
target it goes to and why. It is deterministic and explainable; the
optional LLM agent only writes the justification, it never changes this decision.

Review effort is deliberately handled in ``review.py`` through ``ReviewPlan``.
That keeps technology target selection separate from governance gates.

Target priority (first that applies wins):
  1. No recognized interaction  -> MANUAL REVIEW (cannot be classified)
  2. UI legacy present          -> SELECTIVE RPA (the fragile link rules)
  3. Variant in a large cluster -> shared MICROSERVICE (consolidate)
  4. Database present           -> custom PYTHON/JAVA (data logic)
  5. API / email / file         -> n8n (orchestrable integration)

User-facing reason strings stay in Spanish (the report audience), matching the
project convention of English code with Spanish display text.
"""

from __future__ import annotations

from .entities import Cluster, InteractionType, MigrationTarget, Taskbot

# A cluster is treated as a "reusable utility" (shared microservice candidate)
# from 3 variants on; with 2 it is simple consolidation via n8n.
MICROSERVICE_CLUSTER_MIN_SIZE = 3


def classify_target(
    bot: Taskbot, cluster: Cluster | None
) -> tuple[MigrationTarget, list[str]]:
    """Return (target, reasons) for a taskbot."""
    reasons: list[str] = []
    interactions = set(bot.known_interactions)
    in_big_cluster = cluster is not None and cluster.size >= MICROSERVICE_CLUSTER_MIN_SIZE

    # 1. No recognized interaction type: target cannot be classified.
    if not interactions:
        reasons.append("Tipo de interaccion no reconocido: requiere revision humana.")
        return MigrationTarget.MANUAL_REVIEW, reasons

    # 2. UI legacy present: without clean integration, the target is selective RPA.
    #    The most fragile link (the legacy UI) dominates the migration decision.
    if InteractionType.UI_LEGACY in interactions:
        reasons.append("Depende de UI legacy sin integracion: mantener en RPA selectivo.")
        if in_big_cluster:
            reasons.append(
                f"Es variante dentro de un grupo de {cluster.size}: consolidar el RPA, no duplicarlo."
            )
        return MigrationTarget.RPA_SELECTIVE, reasons

    # 3. Variant in a large cluster (no legacy) => shared component/microservice.
    if in_big_cluster:
        reasons.append(
            f"Variante de una utilidad reutilizable (cluster de {cluster.size}): "
            "consolidar como microservicio/componente compartido."
        )
        return MigrationTarget.MICROSERVICE, reasons

    # 4. Database present: data logic => custom service (Python/Java).
    if InteractionType.DATABASE in interactions:
        reasons.append("Interaccion con BD: automatizacion a la medida en Python/Java.")
        return MigrationTarget.CUSTOM_PYTHON_JAVA, reasons

    # 5. Only API / email / file: orchestrable integration => n8n.
    labels = {
        InteractionType.API: "API-first",
        InteractionType.EMAIL: "email",
        InteractionType.FILE: "archivos",
    }
    # Iterate the ordered tuple (not the set) so the text is deterministic.
    present = ", ".join(labels[i] for i in bot.known_interactions if i in labels)
    reasons.append(f"Integracion orquestable ({present}): candidato a n8n.")
    if cluster is not None and cluster.is_duplicate_group:
        reasons.append(
            f"Ademas es variante de otros {cluster.size - 1} taskbot(s): consolidar el flujo."
        )
    return MigrationTarget.N8N, reasons
