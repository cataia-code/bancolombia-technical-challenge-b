"""Tests de las reglas de clasificacion de destino (nucleo de negocio)."""

from taskbot_advisor.domain.entities import (
    Cluster,
    InteractionType,
    MigrationTarget,
    RiskLevel,
    Taskbot,
)
from taskbot_advisor.domain.rules import classify_target

I = InteractionType


def _bot(**kw) -> Taskbot:
    base = dict(
        id="t1", name="bot", purpose="hace algo", apps=("SAP",),
        interactions=(I.API,), frequency="diaria", risk=RiskLevel.LOW,
        dependencies=(), known_similarity="",
    )
    base.update(kw)
    return Taskbot(**base)


def test_api_va_a_n8n():
    target, reasons, manual = classify_target(_bot(interactions=(I.API,)), None)
    assert target is MigrationTarget.N8N
    assert not manual
    assert reasons


def test_email_y_archivo_van_a_n8n():
    assert classify_target(_bot(interactions=(I.EMAIL,)), None)[0] is MigrationTarget.N8N
    assert classify_target(_bot(interactions=(I.FILE,)), None)[0] is MigrationTarget.N8N


def test_ui_legacy_queda_en_rpa_selectivo():
    target, _, manual = classify_target(_bot(interactions=(I.UI_LEGACY,)), None)
    assert target is MigrationTarget.RPA_SELECTIVE
    assert not manual


def test_ui_legacy_domina_aunque_haya_api_y_bd():
    # El eslabon fragil (UI legacy) manda sobre API/BD presentes.
    bot = _bot(interactions=(I.API, I.DATABASE, I.UI_LEGACY))
    assert classify_target(bot, None)[0] is MigrationTarget.RPA_SELECTIVE


def test_database_sin_legacy_va_a_custom():
    target, _, _ = classify_target(_bot(interactions=(I.DATABASE,)), None)
    assert target is MigrationTarget.CUSTOM_PYTHON_JAVA


def test_api_mas_bd_sin_legacy_va_a_custom():
    target, _, _ = classify_target(_bot(interactions=(I.API, I.DATABASE)), None)
    assert target is MigrationTarget.CUSTOM_PYTHON_JAVA


def test_tipo_desconocido_requiere_revision_manual():
    target, _, manual = classify_target(_bot(interactions=(I.UNKNOWN,)), None)
    assert target is MigrationTarget.MANUAL_REVIEW
    assert manual is True


def test_revision_manual_es_flag_ortogonal():
    # Alto riesgo + muchas dependencias: va a n8n PERO marcado para revision.
    bot = _bot(interactions=(I.API,), risk=RiskLevel.HIGH,
               dependencies=("a", "b", "c"))
    target, _, manual = classify_target(bot, None)
    assert target is MigrationTarget.N8N
    assert manual is True


def test_cluster_grande_no_legacy_es_microservicio():
    cluster = Cluster(id=0, member_ids=("t1", "t2", "t3"), representative_id="t1")
    target, _, _ = classify_target(_bot(interactions=(I.API,)), cluster)
    assert target is MigrationTarget.MICROSERVICE


def test_cluster_grande_legacy_sigue_en_rpa():
    cluster = Cluster(id=0, member_ids=("t1", "t2", "t3"), representative_id="t1")
    target, _, _ = classify_target(_bot(interactions=(I.UI_LEGACY,)), cluster)
    assert target is MigrationTarget.RPA_SELECTIVE
