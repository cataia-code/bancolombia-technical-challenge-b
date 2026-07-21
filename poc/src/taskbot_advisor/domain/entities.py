"""Domain model: pure entities and value objects (no I/O).

This module is the stable core of the solution. It imports nothing from
infrastructure or frameworks: only language types. That makes it trivially
testable and shields the business rules from changes at the edges
(persistence, API, LLM).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InteractionType(str, Enum):
    """Dominant interaction type of a taskbot with the systems."""

    API = "api"
    FILE = "file"
    EMAIL = "email"
    DATABASE = "database"
    UI_LEGACY = "ui_legacy"
    UNKNOWN = "unknown"

    @classmethod
    def parse(cls, raw: str | None) -> "InteractionType":
        """Normalize a single interaction token to a canonical type (fail-soft).

        Accepts common Spanish/English synonyms. For anything unknown it returns
        UNKNOWN instead of failing: an odd value must not break the batch.
        """
        if not raw:
            return cls.UNKNOWN
        value = raw.strip().lower()
        aliases = {
            "api": cls.API, "rest": cls.API, "servicio": cls.API, "webservice": cls.API,
            "archivo": cls.FILE, "file": cls.FILE, "csv": cls.FILE, "excel": cls.FILE, "sftp": cls.FILE,
            "email": cls.EMAIL, "correo": cls.EMAIL, "mail": cls.EMAIL,
            "bd": cls.DATABASE, "db": cls.DATABASE, "database": cls.DATABASE, "sql": cls.DATABASE,
            "ui": cls.UI_LEGACY, "ui legacy": cls.UI_LEGACY, "ui_legacy": cls.UI_LEGACY,
            "legacy": cls.UI_LEGACY, "escritorio": cls.UI_LEGACY, "citrix": cls.UI_LEGACY,
            "mainframe": cls.UI_LEGACY,
        }
        return aliases.get(value, cls.UNKNOWN)

    @classmethod
    def parse_many(cls, raw: str | None) -> tuple["InteractionType", ...]:
        """Parse a multi-valued field ('email, archivo, UI legacy') into a set.

        Real data declares several types per taskbot. Order of appearance is
        preserved, duplicates are removed, and unrecognized tokens are dropped
        (if none is recognized, returns (UNKNOWN,)).
        """
        if not raw:
            return (cls.UNKNOWN,)
        tokens = [t for chunk in raw.split(",") for t in chunk.split("/")]
        seen: list[InteractionType] = []
        for token in tokens:
            parsed = cls.parse(token)
            if parsed is not cls.UNKNOWN and parsed not in seen:
                seen.append(parsed)
        return tuple(seen) if seen else (cls.UNKNOWN,)


class RiskLevel(str, Enum):
    """Declared operational risk of a taskbot."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def parse(cls, raw: str | None) -> "RiskLevel":
        value = (raw or "medium").strip().lower()
        aliases = {
            "bajo": cls.LOW, "low": cls.LOW,
            "medio": cls.MEDIUM, "medium": cls.MEDIUM, "media": cls.MEDIUM,
            "alto": cls.HIGH, "high": cls.HIGH, "alta": cls.HIGH,
        }
        return aliases.get(value, cls.MEDIUM)


class MigrationTarget(str, Enum):
    """Suggested technology target for the taskbot migration."""

    N8N = "n8n"
    MICROSERVICE = "microservice"
    CUSTOM_PYTHON_JAVA = "custom_python_java"
    RPA_SELECTIVE = "rpa_selective"
    MANUAL_REVIEW = "manual_review"


class Wave(str, Enum):
    """Suggested migration wave (execution priority)."""

    WAVE_1 = "ola_1"  # High value, low complexity -> quick wins
    WAVE_2 = "ola_2"  # Intermediate value/complexity
    WAVE_3 = "ola_3"  # Low value or high complexity -> last


class ReviewStrategy(str, Enum):
    """How a governance gate should be handled."""

    NONE = "sin_revision"
    AI_PRECHECK = "prechequeo_ia"
    TARGETED_APPROVAL = "aprobacion_dirigida"
    MANUAL_DEEP_DIVE = "evaluacion_manual_profunda"


@dataclass(frozen=True)
class Taskbot:
    """A taskbot from the inventory. Immutable value object keyed by id."""

    id: str
    name: str
    purpose: str
    apps: tuple[str, ...]
    interactions: tuple[InteractionType, ...]
    frequency: str
    risk: RiskLevel
    dependencies: tuple[str, ...] = ()
    known_similarity: str = ""

    def normalized_text(self) -> str:
        """Canonical text (name + purpose + apps) used for similarity."""
        parts = [self.name, self.purpose, " ".join(self.apps)]
        return " ".join(p for p in parts if p).lower().strip()

    def has(self, interaction: InteractionType) -> bool:
        """True if the taskbot exhibits that interaction type."""
        return interaction in self.interactions

    @property
    def known_interactions(self) -> tuple[InteractionType, ...]:
        """Recognized interaction types (excludes UNKNOWN)."""
        return tuple(i for i in self.interactions if i is not InteractionType.UNKNOWN)


@dataclass(frozen=True)
class Cluster:
    """Group of taskbots detected as variants of the same utility."""

    id: int
    member_ids: tuple[str, ...]
    representative_id: str

    @property
    def size(self) -> int:
        return len(self.member_ids)

    @property
    def is_duplicate_group(self) -> bool:
        """A cluster with 2+ members evidences possible consolidation."""
        return self.size >= 2


@dataclass(frozen=True)
class EvidencePack:
    """Structured evidence that an AI/human reviewer can consume."""

    dependencies: tuple[str, ...] = ()
    controls: tuple[str, ...] = ()
    checklist: tuple[str, ...] = ()
    suggested_owner: str = "arquitectura"
    blockers: tuple[str, ...] = ()
    next_action: str = "Sin accion adicional."


@dataclass(frozen=True)
class ReviewPlan:
    """Governance action required before implementation.

    A high-risk taskbot can require a gate without needing a full manual
    assessment. AI-assisted modes prepare evidence and checklists; only
    MANUAL_DEEP_DIVE represents deep human evaluation.
    """

    strategy: ReviewStrategy = ReviewStrategy.NONE
    reason: str = ""
    action: str = "Sin revision adicional."
    evidence_pack: EvidencePack = field(default_factory=EvidencePack)

    @property
    def requires_governance_gate(self) -> bool:
        return self.strategy is not ReviewStrategy.NONE

    @property
    def is_ai_assisted(self) -> bool:
        return self.strategy in {
            ReviewStrategy.AI_PRECHECK,
            ReviewStrategy.TARGETED_APPROVAL,
        }

    @property
    def needs_manual_review(self) -> bool:
        return self.strategy is ReviewStrategy.MANUAL_DEEP_DIVE


@dataclass(frozen=True)
class MigrationDecision:
    """Target decision independent from scoring and written rationale."""

    target: MigrationTarget
    wave: Wave
    cluster_id: int | None
    reasons: tuple[str, ...] = ()
    review: ReviewPlan = field(default_factory=ReviewPlan)

    @property
    def needs_manual_review(self) -> bool:
        return self.review.needs_manual_review


@dataclass(frozen=True)
class ScoreExplanation:
    """Scores plus their transparent component breakdown."""

    value: float
    complexity: float
    breakdown: dict[str, object] = field(default_factory=dict)


@dataclass
class Recommendation:
    """Actionable recommendation for a taskbot.

    The recommendation composes smaller value objects (decision, scores and API
    enablement). Read-only properties preserve the previous public API used by
    renderers and tests.
    """

    taskbot_id: str
    taskbot_name: str
    decision: MigrationDecision
    scores: ScoreExplanation
    # Natural-language justification (rule + optional agent enrichment).
    rationale: str = ""
    # API enablement view of this operation (see api_enablement.py).
    api_enablement: "ApiEnablement | None" = None

    @property
    def target(self) -> MigrationTarget:
        return self.decision.target

    @property
    def wave(self) -> Wave:
        return self.decision.wave

    @property
    def value_score(self) -> float:
        return self.scores.value

    @property
    def complexity_score(self) -> float:
        return self.scores.complexity

    @property
    def cluster_id(self) -> int | None:
        return self.decision.cluster_id

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.decision.reasons

    @property
    def needs_manual_review(self) -> bool:
        return self.decision.needs_manual_review

    @property
    def review_strategy(self) -> ReviewStrategy:
        return self.decision.review.strategy

    @property
    def review_reason(self) -> str:
        return self.decision.review.reason

    @property
    def review_action(self) -> str:
        return self.decision.review.action

    @property
    def evidence_pack(self) -> "EvidencePack":
        return self.decision.review.evidence_pack

    @property
    def requires_governance_gate(self) -> bool:
        return self.decision.review.requires_governance_gate

    @property
    def ai_assisted_review(self) -> bool:
        return self.decision.review.is_ai_assisted

    @property
    def score_breakdown(self) -> dict[str, object]:
        return self.scores.breakdown


@dataclass(frozen=True)
class ApiEnablement:
    """API/no-API view of one operation (recommendation).

    Answers, per operation: which systems it touches, whether an API is already
    available, whether the target requires one, what blocks it and what action
    would enable migrating off RPA. Makes the "legacy -> RPA" verdict defensible.
    """

    systems: tuple[str, ...]
    api_available: bool
    api_required: bool
    blocker: str | None
    enabling_action: str
    target_after_enablement: MigrationTarget


@dataclass(frozen=True)
class ComponentCandidate:
    """A reusable component that could be extracted from a cluster of variants.

    This is the step from "these are duplicates" to "extract THIS shared
    component": suggested name, members, common purpose, target pattern,
    dominant apps, whether a legacy blocker exists and the recommended action.
    """

    cluster_id: int
    suggested_name: str
    member_ids: tuple[str, ...]
    member_names: tuple[str, ...]
    common_purpose: str
    target_pattern: MigrationTarget
    dominant_apps: tuple[str, ...]
    legacy_blocker: bool
    needs_api_enablement: bool
    recommended_action: str

    @property
    def size(self) -> int:
        return len(self.member_ids)


@dataclass
class AnalysisResult:
    """Full output of an inventory analysis."""

    run_id: str
    recommendations: list[Recommendation]
    clusters: list[Cluster]
    errors: list[dict] = field(default_factory=list)
    # Rationalization plan enrichments (built by the use case).
    component_candidates: list[ComponentCandidate] = field(default_factory=list)
    api_matrix: list[dict] = field(default_factory=list)
    sensitivity: dict[str, object] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.recommendations)

    def by_target(self, target: MigrationTarget) -> list[Recommendation]:
        return [r for r in self.recommendations if r.target == target]

    def by_wave(self, wave: Wave) -> list[Recommendation]:
        return [r for r in self.recommendations if r.wave == wave]

    @property
    def consolidation_groups(self) -> list[Cluster]:
        return [c for c in self.clusters if c.is_duplicate_group]
