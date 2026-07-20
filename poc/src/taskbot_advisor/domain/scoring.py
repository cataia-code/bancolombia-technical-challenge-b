"""Transparent value/complexity scoring and wave assignment.

Scoring is deterministic and explainable: every component of the score is
documented and bounded, so we can always answer "why did this taskbot get this
wave". There are no black boxes here.
"""

from __future__ import annotations

from .entities import InteractionType, RiskLevel, Taskbot, Wave

# --- Frequency -> business value of automating/optimizing (0-40) --------------
# Higher frequency => higher potential saving => higher value of migrating well.
_FREQUENCY_VALUE = {
    "high": 40.0,    # daily, hourly, intraday
    "medium": 25.0,  # weekly
    "low": 10.0,     # monthly, on-demand, manual
}

# --- Intrinsic technical complexity per interaction type (0-40) ---------------
_INTERACTION_COMPLEXITY = {
    InteractionType.API: 10.0,
    InteractionType.EMAIL: 12.0,
    InteractionType.FILE: 18.0,
    InteractionType.DATABASE: 25.0,
    InteractionType.UI_LEGACY: 40.0,   # legacy UI is the hardest to migrate
    InteractionType.UNKNOWN: 35.0,     # the unknown is assumed expensive
}

_RISK_VALUE = {RiskLevel.HIGH: 30.0, RiskLevel.MEDIUM: 18.0, RiskLevel.LOW: 8.0}
_RISK_COMPLEXITY = {RiskLevel.HIGH: 25.0, RiskLevel.MEDIUM: 12.0, RiskLevel.LOW: 4.0}

_CLUSTER_VALUE_BONUS = 30.0  # consolidating duplicates unlocks immediate value
_DEP_COMPLEXITY_PER_ITEM = 5.0
_DEP_COMPLEXITY_CAP = 20.0


def classify_frequency(raw: str | None) -> str:
    """Map free-text frequency to a high/medium/low bucket (fail-soft).

    Recognizes the real-data forms: 'Cada hora', 'Cada 15 minutos',
    'Diario 06:00', 'Tiempo real (evento)', 'Semanal', 'Quincenal', 'Mensual',
    'Bajo demanda'.
    """
    value = (raw or "").strip().lower()
    high_markers = (
        "diari", "daily", "hora", "hourly", "minuto", "intradia", "tiempo real",
        "evento", "cada 15", "cada 10", "cada 20", "cada 30", "cada 2 horas", "cada 4 horas",
    )
    medium_markers = ("semanal", "weekly", "quincenal")
    if any(k in value for k in high_markers):
        return "high"
    if any(k in value for k in medium_markers):
        return "medium"
    return "low"  # monthly, on-demand, manual, or unknown


def value_score(bot: Taskbot, in_duplicate_cluster: bool) -> float:
    """Value score [0-100]: how much this taskbot should be prioritized."""
    score = _FREQUENCY_VALUE[classify_frequency(bot.frequency)]
    score += _RISK_VALUE[bot.risk]
    if in_duplicate_cluster:
        score += _CLUSTER_VALUE_BONUS
    return min(score, 100.0)


def complexity_score(bot: Taskbot) -> float:
    """Complexity score [0-100]: how hard/risky it is to migrate.

    With multiple interaction types the most complex one dominates (e.g. UI
    legacy) and each extra type adds a smaller penalty: integrating several
    channels is harder than a single one.
    """
    interactions = bot.interactions or (InteractionType.UNKNOWN,)
    base = max(_INTERACTION_COMPLEXITY[i] for i in interactions)
    extra_channels = max(len(bot.known_interactions) - 1, 0)
    score = base + extra_channels * 5.0
    score += _RISK_COMPLEXITY[bot.risk]
    score += min(len(bot.dependencies) * _DEP_COMPLEXITY_PER_ITEM, _DEP_COMPLEXITY_CAP)
    return min(score, 100.0)


def value_breakdown(bot: Taskbot, in_duplicate_cluster: bool) -> dict:
    """Explain the value score component by component (for the report)."""
    bucket = classify_frequency(bot.frequency)
    cluster_pts = _CLUSTER_VALUE_BONUS if in_duplicate_cluster else 0.0
    return {
        "frecuencia": {"bucket": bucket, "puntos": _FREQUENCY_VALUE[bucket]},
        "riesgo": {"nivel": bot.risk.value, "puntos": _RISK_VALUE[bot.risk]},
        "duplicidad": {"en_grupo": in_duplicate_cluster, "puntos": cluster_pts},
        "total": value_score(bot, in_duplicate_cluster),
    }


def complexity_breakdown(bot: Taskbot) -> dict:
    """Explain the complexity score component by component (for the report)."""
    interactions = bot.interactions or (InteractionType.UNKNOWN,)
    dominant = max(interactions, key=lambda i: _INTERACTION_COMPLEXITY[i])
    extra = max(len(bot.known_interactions) - 1, 0)
    dep_pts = min(len(bot.dependencies) * _DEP_COMPLEXITY_PER_ITEM, _DEP_COMPLEXITY_CAP)
    return {
        "interaccion_dominante": {"tipo": dominant.value, "puntos": _INTERACTION_COMPLEXITY[dominant]},
        "canales_extra": {"cantidad": extra, "puntos": extra * 5.0},
        "riesgo": {"nivel": bot.risk.value, "puntos": _RISK_COMPLEXITY[bot.risk]},
        "dependencias": {"cantidad": len(bot.dependencies), "puntos": dep_pts},
        "total": complexity_score(bot),
    }


def score_breakdown(bot: Taskbot, in_duplicate_cluster: bool) -> dict:
    """Full, explainable breakdown of value and complexity."""
    return {
        "valor": value_breakdown(bot, in_duplicate_cluster),
        "complejidad": complexity_breakdown(bot),
    }


def assign_wave(value: float, complexity: float, needs_manual_review: bool) -> Wave:
    """Assign a wave: Wave 1 = high value and low complexity (quick wins).

    Cases that require manual review are deferred to Wave 3: they must not enter
    a migration train before their uncertainty is resolved.
    """
    if needs_manual_review:
        return Wave.WAVE_3
    if value >= 50.0 and complexity <= 40.0:
        return Wave.WAVE_1
    if value >= 40.0 and complexity <= 65.0:
        return Wave.WAVE_2
    return Wave.WAVE_3
