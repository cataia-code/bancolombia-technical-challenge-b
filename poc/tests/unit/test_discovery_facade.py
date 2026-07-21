"""Tests for the Part A-compatible discovery facade."""

from pathlib import Path

from taskbot_advisor.discovery import (
    api_matrix,
    cluster_taskbots,
    priority_score,
    run_discovery,
)
from taskbot_advisor.domain.entities import InteractionType, RiskLevel, Taskbot


def _bot(bot_id: str, *, interactions=(InteractionType.API,), apps=("SAP",)) -> Taskbot:
    return Taskbot(
        id=bot_id,
        name=f"Bot {bot_id}",
        purpose="process data",
        apps=apps,
        interactions=interactions,
        frequency="daily",
        risk=RiskLevel.LOW,
    )


def test_cluster_taskbots_keeps_part_a_name():
    bots = [_bot("a"), _bot("b")]
    clusters = cluster_taskbots(bots, lambda _a, _b: 100.0, threshold=82.0)
    assert len(clusters) == 1
    assert clusters[0].member_ids == ("a", "b")


def test_priority_score_is_bounded():
    score = priority_score(_bot("a"), in_duplicate_cluster=True)
    assert 0.0 <= score <= 100.0


def test_api_matrix_keeps_part_a_name():
    rows = api_matrix([_bot("a", interactions=(InteractionType.UI_LEGACY,), apps=("Legacy",))])
    assert rows[0]["sistema"] == "Legacy"
    assert rows[0]["requiere_habilitacion_api"] is True


def test_run_discovery_returns_analysis_result():
    inventory = Path(__file__).resolve().parents[2] / "data" / "ejemplo_50_taskbots_prueba.txt"
    result = run_discovery(inventory, run_id="facade")
    assert result.run_id == "facade"
    assert result.total == 50
