"""Input guardrails for the HTTP surface (defense in depth).

The API can be exposed to an external orchestrator through a controlled ingress.
These helpers prevent two abuses of the /analyze endpoint:

  - Arbitrary local file reads: an ``inventory_path`` is only accepted inside a
    configured ``TASKBOT_INVENTORY_ROOT`` (path traversal is rejected).
  - Path/traversal via ``run_id``: it must match a strict allow-list pattern, so
    it can never escape the reports directory.

For untrusted external exposure the recommended endpoint is ``/analyze/inline``
(the inventory travels in the body; no local path is involved).
"""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class SecurityError(ValueError):
    """A request violated an input guardrail."""


def validate_run_id(run_id: str | None) -> str | None:
    """Return the run_id if it is a safe token, else raise SecurityError."""
    if run_id is None:
        return None
    if not _RUN_ID_RE.match(run_id):
        raise SecurityError(
            "run_id invalido: use 1-64 caracteres [A-Za-z0-9_-] que inicien alfanumerico."
        )
    return run_id


def resolve_inventory_path(path_str: str, inventory_root: str | None) -> str:
    """Resolve an inventory path, containing it within ``inventory_root`` if set.

    When a root is configured, the path is always interpreted relative to it and
    must resolve inside it (rejects absolute paths and ``..`` traversal). When no
    root is configured (default local dev), the path is returned as-is.
    """
    if not inventory_root:
        return path_str
    if Path(path_str).is_absolute() or PureWindowsPath(path_str).is_absolute():
        raise SecurityError("inventory_path debe ser relativo a TASKBOT_INVENTORY_ROOT.")
    base = Path(inventory_root).resolve()
    candidate = Path(path_str)
    resolved = (base / candidate).resolve()
    if base != resolved and base not in resolved.parents:
        raise SecurityError(
            f"inventory_path fuera de TASKBOT_INVENTORY_ROOT ({inventory_root})."
        )
    return str(resolved)
