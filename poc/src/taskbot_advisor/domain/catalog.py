"""Reusable-component catalog: from duplicate clusters to extractable components.

The challenge asks explicitly "which reusable components could be extracted". A
cluster only says "these are variants"; this module turns each duplicate cluster
into a ``ComponentCandidate`` with a suggested name, common purpose, target
pattern, dominant apps, legacy blocker and a recommended action.
"""

from __future__ import annotations

from collections import Counter

from .entities import (
    Cluster,
    ComponentCandidate,
    InteractionType,
    MigrationTarget,
    Recommendation,
    Taskbot,
)

# Tokens too generic to name a component after.
_STOPWORDS = {
    "tb", "de", "del", "la", "el", "los", "las", "por", "con", "para", "y", "en",
    "datos", "gestion", "proceso", "automatico", "diario", "diaria", "masivo",
}


def _significant_tokens(name: str) -> list[str]:
    raw = name.lower().replace("tb_", " ").replace("_", " ")
    return [t for t in raw.split() if len(t) > 2 and t not in _STOPWORDS]


def _suggest_name(names: tuple[str, ...]) -> str:
    """Suggest a component name from tokens shared by most member names.

    Deterministic: tokens are deduped preserving order and ranked by frequency
    desc then alphabetically (never relies on set iteration order, which varies
    per process via hash randomization).
    """
    counts: Counter[str] = Counter()
    for name in names:
        for tok in dict.fromkeys(_significant_tokens(name)):
            counts[tok] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    threshold = max(2, (len(names) + 1) // 2)  # present in at least half
    shared = [tok for tok, n in ranked if n >= threshold]
    if not shared:
        # Fallback: the top-ranked single token, else the first member.
        shared = [ranked[0][0]] if ranked else [names[0]]
    label = " ".join(w.capitalize() for w in shared[:3])
    return f"Componente {label}"


def _common_purpose(members: list[Taskbot]) -> str:
    """Pick a representative common purpose (the shortest is usually the cleanest)."""
    purposes = [m.purpose for m in members if m.purpose]
    return min(purposes, key=len) if purposes else ""


def _dominant_apps(members: list[Taskbot], limit: int = 3) -> tuple[str, ...]:
    counts: Counter[str] = Counter()
    for m in members:
        counts.update(m.apps)
    return tuple(app for app, _ in counts.most_common(limit))


def build_component_candidates(
    clusters: list[Cluster],
    bots_by_id: dict[str, Taskbot],
    recs_by_id: dict[str, Recommendation],
) -> list[ComponentCandidate]:
    """Build one ComponentCandidate per consolidatable cluster (size >= 2)."""
    candidates: list[ComponentCandidate] = []
    for cluster in clusters:
        if not cluster.is_duplicate_group:
            continue
        members = [bots_by_id[i] for i in cluster.member_ids if i in bots_by_id]
        if not members:
            continue
        names = tuple(m.name for m in members)
        targets = [recs_by_id[i].target for i in cluster.member_ids if i in recs_by_id]
        target_pattern = (
            Counter(targets).most_common(1)[0][0] if targets else MigrationTarget.N8N
        )
        legacy_blocker = any(m.has(InteractionType.UI_LEGACY) for m in members)
        api_available_all = all(m.has(InteractionType.API) for m in members)
        needs_api = legacy_blocker and not api_available_all

        if legacy_blocker:
            action = (
                "Consolidar como componente RPA compartido y planear exposicion de API "
                "para migrarlo fuera de RPA en una ola posterior."
            )
        elif target_pattern is MigrationTarget.MICROSERVICE:
            action = "Extraer un microservicio/componente compartido y retirar las variantes."
        else:
            action = "Unificar en un unico flujo n8n reutilizable y retirar los duplicados."

        candidates.append(
            ComponentCandidate(
                cluster_id=cluster.id,
                suggested_name=_suggest_name(names),
                member_ids=cluster.member_ids,
                member_names=names,
                common_purpose=_common_purpose(members),
                target_pattern=target_pattern,
                dominant_apps=_dominant_apps(members),
                legacy_blocker=legacy_blocker,
                needs_api_enablement=needs_api,
                recommended_action=action,
            )
        )
    return candidates
