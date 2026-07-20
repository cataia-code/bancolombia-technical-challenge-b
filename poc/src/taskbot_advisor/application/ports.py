"""Ports (interfaces) the application layer requires from infrastructure.

They are defined as ``Protocol`` (structural typing): infrastructure adapters
satisfy the contract without inheriting anything, and the use case depends only
on these abstractions (Dependency Inversion + Interface Segregation). Each port
is small and single-responsibility.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.entities import AnalysisResult, Recommendation, Taskbot


class InventoryRepository(Protocol):
    """Source of the taskbot inventory (CSV, JSON, SQLite, ...)."""

    def load(self) -> tuple[list[Taskbot], list[dict]]:
        """Return (valid_taskbots, per_record_errors).

        Invalid records do NOT abort the load: they are reported as errors
        (fail-soft) so the batch continues with whatever is processable.
        """
        ...


class SimilarityScorer(Protocol):
    """Computes the similarity [0-100] between two taskbots."""

    def score(self, a: Taskbot, b: Taskbot) -> float:
        ...


@runtime_checkable
class TrainableSimilarityScorer(SimilarityScorer, Protocol):
    """Similarity scorer that can calibrate itself from the full portfolio."""

    def fit(self, bots: list[Taskbot]) -> None:
        ...


class AgentAdvisor(Protocol):
    """Enriches an already-decided recommendation with a written justification.

    It NEVER changes the decision (target/wave): it only produces explanatory
    text. The default implementation is deterministic; an LLM implementation is
    optional.
    """

    def explain(self, bot: Taskbot, recommendation: Recommendation) -> str:
        ...


class ReportRenderer(Protocol):
    """Serializes the analysis result to a concrete format (JSON, HTML)."""

    extension: str

    def render(self, result: AnalysisResult) -> str:
        ...


class RunLogger(Protocol):
    """Observability port for run-scoped structured events."""

    def info(self, event: str, **fields: object) -> None:
        ...

    def error(self, event: str, exc_info: bool = False, **fields: object) -> None:
        ...


class RunLoggerFactory(Protocol):
    """Creates a logger bound to a generated or user-provided run_id."""

    def for_run(self, run_id: str) -> RunLogger:
        ...


class NullRunLogger:
    """No-op logger for tests or embedded use without observability wiring."""

    def info(self, event: str, **fields: object) -> None:
        return None

    def error(self, event: str, exc_info: bool = False, **fields: object) -> None:
        return None


class NullRunLoggerFactory:
    """Default logger factory that keeps the use case independent of infra."""

    def for_run(self, run_id: str) -> RunLogger:
        return NullRunLogger()
