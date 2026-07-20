"""Similarity adapter: combines three signals to detect variants.

  1. DECLARED duplicate evidence (inventory field 'Similar a TB_X'): if a taskbot
     references the other by name, this is the strongest, most reliable signal.
  2. Application/system overlap (Jaccard index) EXCLUDING 'hub' apps.
  3. Textual similarity of name + purpose (rapidfuzz token_set_ratio).

'Hub' apps: systems present in a large share of the portfolio (e.g. SAP ECC).
They are not discriminative and, if used to group, would chain distinct
capabilities together (the classic single-linkage problem). Hence they are
ignored in the overlap, and a declared reference only merges if it also shares a
NON-hub app.

Implements the ``SimilarityScorer`` port without the domain knowing rapidfuzz.
"""

from __future__ import annotations

import math
import re

from rapidfuzz import fuzz

from ..domain.entities import Taskbot

# Score when there is declared evidence AND they share a non-hub app (merges).
_DECLARED_STRONG = 90.0
# Score when there is declared evidence but NO shared non-hub app (won't merge alone).
_DECLARED_WEAK = 78.0
# An app is considered 'hub' if it appears in at least this fraction of the portfolio.
_HUB_FRACTION = 0.25


class RapidFuzzSimilarity:
    def __init__(self, apps_overlap_weight: float = 0.35) -> None:
        self._w_apps = max(0.0, min(1.0, apps_overlap_weight))
        self._hub_apps: set[str] = set()

    def fit(self, bots: list[Taskbot]) -> None:
        """Learn the portfolio's 'hub' apps (called by the use case)."""
        if not bots:
            self._hub_apps = set()
            return
        counts: dict[str, int] = {}
        for bot in bots:
            for app in {a.lower() for a in bot.apps}:
                counts[app] = counts.get(app, 0) + 1
        cutoff = max(2, math.ceil(_HUB_FRACTION * len(bots)))
        self._hub_apps = {app for app, n in counts.items() if n >= cutoff}

    def _nonhub(self, bot: Taskbot) -> set[str]:
        return {a.lower() for a in bot.apps} - self._hub_apps

    def score(self, a: Taskbot, b: Taskbot) -> float:
        text = fuzz.token_set_ratio(a.normalized_text(), b.normalized_text())
        nonhub_a, nonhub_b = self._nonhub(a), self._nonhub(b)
        apps = _jaccard(nonhub_a, nonhub_b) * 100.0
        blended = (1.0 - self._w_apps) * text + self._w_apps * apps

        if _declares(a, b) or _declares(b, a):
            shares_nonhub = bool(nonhub_a & nonhub_b)
            # Declared + shared discriminative app => merge. Without it, a weak
            # signal (does not chain distinct capabilities that only share a hub
            # such as SAP).
            return max(blended, _DECLARED_STRONG if shares_nonhub else _DECLARED_WEAK)
        return blended


def _tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) > 2}


def _declares(a: Taskbot, b: Taskbot) -> bool:
    """True if ``a`` mentions ``b`` in its declared duplicate evidence."""
    evidence = a.known_similarity.lower()
    if not evidence:
        return False
    if b.name.lower() in evidence:
        return True
    b_tokens = _tokens(b.name)
    if not b_tokens:
        return False
    overlap = b_tokens & _tokens(evidence)
    return len(overlap) >= max(2, len(b_tokens) - 1)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
