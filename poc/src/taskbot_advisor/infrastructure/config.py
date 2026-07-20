"""Centralized, explicit configuration (Explicit Dependencies + Fail Fast).

All configuration is resolved here from environment variables with safe
defaults. There is no scattered environment reading across the code: the domain
and use cases receive an immutable ``Settings`` object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Execution parameters. Immutable to avoid accidental mutation."""

    # Threshold [0-100] above which two taskbots are considered variants.
    similarity_threshold: float = 82.0
    # Weight of app overlap when combined with textual similarity.
    apps_overlap_weight: float = 0.35
    # Root directory where reports are written (one subfolder per runId).
    reports_dir: str = "reports"
    # Enables the LLM agent layer. If False (or no API key) the deterministic
    # fallback advisor is used. The solution NEVER depends on the LLM.
    llm_enabled: bool = False
    llm_model: str = "claude-opus-4-8"
    llm_api_key: str | None = None

    @staticmethod
    def from_env() -> "Settings":
        """Build Settings from the environment. Fail-fast on invalid values."""
        threshold = _read_float("TASKBOT_SIMILARITY_THRESHOLD", 82.0)
        if not 0.0 <= threshold <= 100.0:
            raise ValueError(
                f"TASKBOT_SIMILARITY_THRESHOLD must be in [0,100], got: {threshold}"
            )
        api_key = os.getenv("ANTHROPIC_API_KEY") or None
        llm_enabled = os.getenv("TASKBOT_LLM_ENABLED", "false").lower() == "true"
        return Settings(
            similarity_threshold=threshold,
            apps_overlap_weight=_read_float("TASKBOT_APPS_OVERLAP_WEIGHT", 0.35),
            reports_dir=os.getenv("TASKBOT_REPORTS_DIR", "reports"),
            # The LLM is only activated if explicitly enabled AND a credential exists.
            llm_enabled=llm_enabled and api_key is not None,
            llm_model=os.getenv("TASKBOT_LLM_MODEL", "claude-opus-4-8"),
            llm_api_key=api_key,
        )


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:  # Fail-fast: invalid config must not pass silently.
        raise ValueError(f"{name} must be numeric, got: {raw!r}") from exc
