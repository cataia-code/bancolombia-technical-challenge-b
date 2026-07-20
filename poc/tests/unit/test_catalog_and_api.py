"""Tests for the reusable-component catalog, API enablement and score breakdown."""

from taskbot_advisor.domain import api_enablement, scoring
from taskbot_advisor.domain.catalog import build_component_candidates
from taskbot_advisor.domain.entities import (
    Cluster,
    InteractionType,
    MigrationTarget,
    Recommendation,
    RiskLevel,
    Taskbot,
    Wave,
)

I = InteractionType


def _bot(id_, name, interactions=(I.API,), apps=("SAP ECC",), purpose="hace algo",
         risk=RiskLevel.LOW, deps=()):
    return Taskbot(id=id_, name=name, purpose=purpose, apps=apps, interactions=interactions,
                   frequency="diaria", risk=risk, dependencies=deps)


def _rec(bot, target):
    return Recommendation(taskbot_id=bot.id, taskbot_name=bot.name, target=target,
                          wave=Wave.WAVE_2, value_score=50, complexity_score=30, cluster_id=0)


# ---------------- API enablement (per operation) ----------------

def test_api_enablement_legacy_sin_api_marca_bloqueador_y_accion():
    bot = _bot("1", "X", interactions=(I.UI_LEGACY,))
    e = api_enablement.assess(bot, MigrationTarget.RPA_SELECTIVE)
    assert e.blocker == "ui_legacy"
    assert e.api_required is True
    assert "Exponer" in e.enabling_action


def test_api_enablement_api_disponible_sin_bloqueador():
    bot = _bot("1", "X", interactions=(I.API,))
    e = api_enablement.assess(bot, MigrationTarget.N8N)
    assert e.blocker is None
    assert e.api_available is True


def test_api_enablement_database_sin_api():
    bot = _bot("1", "X", interactions=(I.DATABASE,))
    e = api_enablement.assess(bot, MigrationTarget.CUSTOM_PYTHON_JAVA)
    assert e.blocker == "database"


def test_api_enablement_unknown_evalua():
    bot = _bot("1", "X", interactions=(I.UNKNOWN,))
    e = api_enablement.assess(bot, MigrationTarget.MANUAL_REVIEW)
    assert e.blocker is None
    assert "Evaluar" in e.enabling_action


def test_system_matrix_agrega_por_sistema():
    bots = [
        _bot("1", "A", interactions=(I.UI_LEGACY,), apps=("SAP ECC",)),
        _bot("2", "B", interactions=(I.API,), apps=("SAP ECC", "Salesforce")),
    ]
    matrix = api_enablement.system_matrix(bots)
    sap = next(r for r in matrix if r["sistema"] == "SAP ECC")
    assert sap["taskbots"] == 2
    assert sap["api_disponible"] is True          # B expone API sobre SAP
    assert sap["requiere_habilitacion_api"] is False


def test_system_matrix_legacy_sin_api_requiere_habilitacion():
    bots = [_bot("1", "A", interactions=(I.UI_LEGACY,), apps=("Mainframe",))]
    matrix = api_enablement.system_matrix(bots)
    assert matrix[0]["requiere_habilitacion_api"] is True


# ---------------- Component catalog ----------------

def test_component_candidate_desde_cluster():
    b1 = _bot("1", "TB_Alta_Proveedores_Maestro", interactions=(I.API,))
    b2 = _bot("2", "TB_Actualizacion_Datos_Proveedores", interactions=(I.API,))
    cluster = Cluster(id=0, member_ids=("1", "2"), representative_id="1")
    bots_by_id = {"1": b1, "2": b2}
    recs = {"1": _rec(b1, MigrationTarget.N8N), "2": _rec(b2, MigrationTarget.N8N)}
    cands = build_component_candidates([cluster], bots_by_id, recs)
    assert len(cands) == 1
    c = cands[0]
    assert "proveedores" in c.suggested_name.lower()
    assert c.size == 2
    assert c.target_pattern is MigrationTarget.N8N
    assert c.legacy_blocker is False


def test_component_candidate_legacy_requiere_api_enablement():
    b1 = _bot("1", "TB_Carga_SAP", interactions=(I.UI_LEGACY,))
    b2 = _bot("2", "TB_Carga_SAP_Alt", interactions=(I.UI_LEGACY,))
    b3 = _bot("3", "TB_Carga_SAP_Bis", interactions=(I.UI_LEGACY,))
    cluster = Cluster(id=0, member_ids=("1", "2", "3"), representative_id="1")
    bots_by_id = {"1": b1, "2": b2, "3": b3}
    recs = {i: _rec(bots_by_id[i], MigrationTarget.RPA_SELECTIVE) for i in ("1", "2", "3")}
    cands = build_component_candidates([cluster], bots_by_id, recs)
    assert cands[0].legacy_blocker is True
    assert cands[0].needs_api_enablement is True
    assert "RPA" in cands[0].recommended_action


def test_component_candidate_microservicio():
    b = [_bot(str(i), f"TB_Cliente_{i}", interactions=(I.API,)) for i in range(3)]
    cluster = Cluster(id=0, member_ids=("0", "1", "2"), representative_id="0")
    bots_by_id = {x.id: x for x in b}
    recs = {x.id: _rec(x, MigrationTarget.MICROSERVICE) for x in b}
    c = build_component_candidates([cluster], bots_by_id, recs)[0]
    assert c.target_pattern is MigrationTarget.MICROSERVICE
    assert "microservicio" in c.recommended_action.lower()


def test_catalog_ignora_clusters_de_uno():
    cluster = Cluster(id=0, member_ids=("1",), representative_id="1")
    assert build_component_candidates([cluster], {"1": _bot("1", "X")}, {}) == []


def test_catalog_ignora_cluster_sin_miembros_conocidos():
    # Cluster consolidable pero cuyos ids no están en bots_by_id (todos fallaron).
    cluster = Cluster(id=0, member_ids=("9", "8"), representative_id="9")
    assert build_component_candidates([cluster], {}, {}) == []


def test_suggested_name_fallback_sin_tokens_compartidos():
    b1 = _bot("1", "TB_Uno", interactions=(I.API,))
    b2 = _bot("2", "TB_Dos", interactions=(I.API,))
    cluster = Cluster(id=0, member_ids=("1", "2"), representative_id="1")
    c = build_component_candidates(
        [cluster], {"1": b1, "2": b2},
        {"1": _rec(b1, MigrationTarget.N8N), "2": _rec(b2, MigrationTarget.N8N)},
    )[0]
    assert c.suggested_name.startswith("Componente")


# ---------------- Score breakdown ----------------

def test_score_breakdown_estructura_y_totales():
    bot = _bot("1", "X", interactions=(I.API, I.DATABASE), risk=RiskLevel.HIGH,
               deps=("a", "b"))
    bd = scoring.score_breakdown(bot, in_duplicate_cluster=True)
    assert bd["valor"]["duplicidad"]["puntos"] == 30.0
    assert bd["valor"]["total"] == scoring.value_score(bot, True)
    assert bd["complejidad"]["interaccion_dominante"]["tipo"] == "database"
    assert bd["complejidad"]["canales_extra"]["cantidad"] == 1
    assert bd["complejidad"]["total"] == scoring.complexity_score(bot)
