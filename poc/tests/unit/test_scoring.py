"""Tests del scoring de valor/complejidad y asignacion de ola."""

from taskbot_advisor.domain.entities import InteractionType, RiskLevel, Taskbot, Wave
from taskbot_advisor.domain.scoring import (
    assign_wave,
    classify_frequency,
    complexity_score,
    value_score,
)


def _bot(**kw) -> Taskbot:
    base = dict(
        id="t1", name="bot", purpose="p", apps=(), interactions=(InteractionType.API,),
        frequency="diaria", risk=RiskLevel.LOW, dependencies=(), known_similarity="",
    )
    base.update(kw)
    return Taskbot(**base)


def test_classify_frequency_buckets():
    assert classify_frequency("Diaria") == "high"
    assert classify_frequency("semanal") == "medium"
    assert classify_frequency("mensual") == "low"
    assert classify_frequency(None) == "low"


def test_valor_sube_con_frecuencia_y_cluster():
    baja = value_score(_bot(frequency="mensual"), in_duplicate_cluster=False)
    alta = value_score(_bot(frequency="diaria"), in_duplicate_cluster=True)
    assert alta > baja


def test_complejidad_ui_legacy_mayor_que_api():
    api = complexity_score(_bot(interactions=(InteractionType.API,)))
    legacy = complexity_score(_bot(interactions=(InteractionType.UI_LEGACY,)))
    assert legacy > api


def test_dependencias_incrementan_complejidad_con_tope():
    sin = complexity_score(_bot(dependencies=()))
    con = complexity_score(_bot(dependencies=("a", "b", "c", "d", "e", "f")))
    assert con > sin
    assert con <= 100.0


def test_ola_1_alto_valor_baja_complejidad():
    assert assign_wave(value=80, complexity=30, needs_manual_review=False) is Wave.WAVE_1


def test_ola_3_para_revision_manual_aunque_valor_alto():
    assert assign_wave(value=90, complexity=20, needs_manual_review=True) is Wave.WAVE_3


def test_ola_3_alta_complejidad():
    assert assign_wave(value=30, complexity=90, needs_manual_review=False) is Wave.WAVE_3


def test_scores_acotados_0_100():
    bot = _bot(frequency="diaria", risk=RiskLevel.HIGH, dependencies=("a", "b", "c", "d", "e"))
    assert 0 <= value_score(bot, True) <= 100
    assert 0 <= complexity_score(bot) <= 100
