"""Tests de las reglas de clasificacion de destino (nucleo de negocio)."""

from taskbot_advisor.domain.entities import (
    Cluster,
    InteractionType,
    MigrationTarget,
    ReviewStrategy,
    RiskLevel,
    Taskbot,
)
from taskbot_advisor.domain.review import (
    ReviewSensitivityInput,
    assess_review,
    build_review_sensitivity,
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
    target, reasons = classify_target(_bot(interactions=(I.API,)), None)
    assert target is MigrationTarget.N8N
    assert reasons


def test_email_y_archivo_van_a_n8n():
    assert classify_target(_bot(interactions=(I.EMAIL,)), None)[0] is MigrationTarget.N8N
    assert classify_target(_bot(interactions=(I.FILE,)), None)[0] is MigrationTarget.N8N


def test_ui_legacy_queda_en_rpa_selectivo():
    target, _ = classify_target(_bot(interactions=(I.UI_LEGACY,)), None)
    assert target is MigrationTarget.RPA_SELECTIVE


def test_ui_legacy_domina_aunque_haya_api_y_bd():
    # El eslabon fragil (UI legacy) manda sobre API/BD presentes.
    bot = _bot(interactions=(I.API, I.DATABASE, I.UI_LEGACY))
    assert classify_target(bot, None)[0] is MigrationTarget.RPA_SELECTIVE


def test_database_sin_legacy_va_a_custom():
    target, _ = classify_target(_bot(interactions=(I.DATABASE,)), None)
    assert target is MigrationTarget.CUSTOM_PYTHON_JAVA


def test_api_mas_bd_sin_legacy_va_a_custom():
    target, _ = classify_target(_bot(interactions=(I.API, I.DATABASE)), None)
    assert target is MigrationTarget.CUSTOM_PYTHON_JAVA


def test_tipo_desconocido_requiere_revision_manual():
    bot = _bot(interactions=(I.UNKNOWN,))
    target, _ = classify_target(bot, None)
    review = assess_review(bot, None, target, complexity=35.0)
    assert target is MigrationTarget.MANUAL_REVIEW
    assert review.needs_manual_review is True
    assert review.strategy is ReviewStrategy.MANUAL_DEEP_DIVE


def test_alto_riesgo_api_va_a_prechequeo_ia():
    # Alto riesgo + muchas dependencias: va a n8n con gate asistido, no manual profundo.
    bot = _bot(interactions=(I.API,), risk=RiskLevel.HIGH,
               dependencies=("a", "b", "c"))
    target, _ = classify_target(bot, None)
    review = assess_review(bot, None, target, complexity=50.0)
    assert target is MigrationTarget.N8N
    assert review.requires_governance_gate is True
    assert review.is_ai_assisted is True
    assert review.needs_manual_review is False
    assert review.evidence_pack.dependencies == ("a", "b", "c")
    assert "verificar dependencias declaradas" in review.evidence_pack.checklist
    assert review.evidence_pack.suggested_owner == "equipo integracion/n8n"


def test_alto_riesgo_extremo_si_requiere_manual_profunda():
    bot = _bot(interactions=(I.API, I.UI_LEGACY), risk=RiskLevel.HIGH,
               dependencies=("a", "b", "c"))
    target, _ = classify_target(bot, None)
    review = assess_review(bot, None, target, complexity=90.0)
    assert target is MigrationTarget.RPA_SELECTIVE
    assert review.strategy is ReviewStrategy.MANUAL_DEEP_DIVE
    assert "ui_legacy" in review.evidence_pack.blockers


def test_sensitivity_recalcula_gate_manual_y_delta():
    bot = _bot(interactions=(I.API,), risk=RiskLevel.HIGH,
               dependencies=("a", "b", "c"))
    target, _ = classify_target(bot, None)
    data = build_review_sensitivity(
        [ReviewSensitivityInput(bot, None, target, value=80.0, complexity=90.0)],
        complexity_thresholds=(85.0, 90.0),
        dependency_thresholds=(3, 4),
    )
    scenarios = {
        (
            s["umbral_dependencias_gate_gobierno"],
            s["umbral_complejidad_manual_profunda"],
        ): s
        for s in data["escenarios"]
    }
    base = scenarios[(3, 85.0)]
    relaxed_complexity = scenarios[(3, 90.0)]
    relaxed_dependencies = scenarios[(4, 85.0)]
    assert base["revision"]["gate_gobierno"] == 1
    assert base["revision"]["manual_profunda"] == 1
    assert relaxed_complexity["revision"]["manual_profunda"] == 0
    assert relaxed_complexity["revision"]["asistida_ia"] == 1
    assert relaxed_complexity["delta_vs_base"]["manual_profunda"] == -1
    assert relaxed_dependencies["revision"]["gate_gobierno"] == 0


def test_cluster_grande_no_legacy_es_microservicio():
    cluster = Cluster(id=0, member_ids=("t1", "t2", "t3"), representative_id="t1")
    target, _ = classify_target(_bot(interactions=(I.API,)), cluster)
    assert target is MigrationTarget.MICROSERVICE


def test_cluster_grande_legacy_sigue_en_rpa():
    cluster = Cluster(id=0, member_ids=("t1", "t2", "t3"), representative_id="t1")
    target, _ = classify_target(_bot(interactions=(I.UI_LEGACY,)), cluster)
    assert target is MigrationTarget.RPA_SELECTIVE
