"""Ports (interfaces) the application layer requires from infrastructure.

They are defined as ``Protocol`` (structural typing): infrastructure adapters
satisfy the contract without inheriting anything, and the use case depends only
on these abstractions (Dependency Inversion + Interface Segregation). Each port
is small and single-responsibility.
"""

from __future__ import annotations

from typing import Protocol

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
