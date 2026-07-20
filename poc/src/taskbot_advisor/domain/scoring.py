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
