"""Domain error hierarchy (separation of concerns for errors).

Distinguishing errors lets each layer respond differently: validation and
inventory -> fail-soft per item; configuration -> fail-fast.
"""

from __future__ import annotations


class TaskbotAdvisorError(Exception):
    """Root of all solution-specific errors."""


class InvalidTaskbotError(TaskbotAdvisorError):
    """An inventory record cannot be turned into a valid Taskbot."""


class InventoryLoadError(TaskbotAdvisorError):
    """The inventory source could not be read (missing file, invalid format)."""
