"""Duplicate detection: groups taskbots into clusters of variants.

The clustering *algorithm* lives here (domain, pure and testable): it receives
an injected similarity function and groups by connected components (union-find).
The concrete similarity *computation* (rapidfuzz, embeddings, etc.) lives in
infrastructure, behind this abstraction (Dependency Inversion).
"""

from __future__ import annotations

from typing import Callable

from .entities import Cluster, Taskbot

# A similarity function receives two taskbots and returns a score in [0-100].
SimilarityFn = Callable[[Taskbot, Taskbot], float]


def build_clusters(
    bots: list[Taskbot], score_fn: SimilarityFn, threshold: float
) -> list[Cluster]:
    """Group taskbots whose pairwise similarity exceeds ``threshold`` (transitive).

    Uses union-find: if A~B and B~C, then A, B and C end up in the same cluster
    even if A~C does not exceed the threshold directly. This reflects that the
    variants of a utility form a connected family.
    """
    n = len(bots)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(n):
        for j in range(i + 1, n):
            if score_fn(bots[i], bots[j]) >= threshold:
                union(i, j)

    # Group indices by root.
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    clusters: list[Cluster] = []
    for cluster_id, (_, members) in enumerate(sorted(groups.items())):
        member_ids = tuple(bots[i].id for i in members)
        # Stable representative: the first id in order of appearance.
        clusters.append(
            Cluster(id=cluster_id, member_ids=member_ids, representative_id=member_ids[0])
        )
    return clusters


def cluster_of(bot_id: str, clusters: list[Cluster]) -> Cluster | None:
    """Return the cluster that contains ``bot_id`` (or None)."""
    for cluster in clusters:
        if bot_id in cluster.member_ids:
            return cluster
    return None
