"""Tests de cobertura fina: entidades, logging estructurado, mapping, similitud."""

import json

from taskbot_advisor.domain.entities import (
    AnalysisResult,
    Cluster,
    InteractionType,
    RiskLevel,
)
from taskbot_advisor.infrastructure.logging import get_logger
from taskbot_advisor.infrastructure.mapping import _split_list, to_taskbot
from taskbot_advisor.infrastructure.similarity_rapidfuzz import RapidFuzzSimilarity

I = InteractionType


def test_interaction_parse_none_y_desconocido():
    assert I.parse(None) is I.UNKNOWN
    assert I.parse("cosa-rara") is I.UNKNOWN


def test_risk_parse_default_y_sinonimos():
    assert RiskLevel.parse(None) is RiskLevel.MEDIUM
    assert RiskLevel.parse("ALTA") is RiskLevel.HIGH


def test_cluster_representante_y_flags():
    c = Cluster(id=0, member_ids=("a",), representative_id="a")
    assert c.is_duplicate_group is False
    assert AnalysisResult("r", [], [c]).consolidation_groups == []


def test_split_list_valor_unico_sin_separador():
    assert _split_list("uno solo") == ("uno solo",)
    assert _split_list("") == ()


def test_to_taskbot_id_derivado_del_nombre():
    bot = to_taskbot({"nombre": "Bot Sin Id"})
    assert bot.id == "bot_sin_id"


def test_logger_emite_json_con_run_id(capsys):
    # Nombre unico: evita reusar un handler cacheado ligado a otro stderr.
    log = get_logger("run-123", name="test_logger_unico")
    log.info("evento_prueba", extra={"k": "v"})
    try:
        raise ValueError("x")
    except ValueError:
        log.error("fallo", exc_info=True)
    err = capsys.readouterr().err.strip().splitlines()
    first = json.loads(err[0])
    assert first["run_id"] == "run-123"
    assert first["k"] == "v"
    assert any("error" in json.loads(line) for line in err)


def test_similarity_jaccard_apps_vacias_no_falla():
    sim = RapidFuzzSimilarity()
    from taskbot_advisor.domain.entities import Taskbot
    a = Taskbot(id="1", name="Alta Clientes", purpose="crear", apps=(),
                interactions=(I.API,), frequency="d", risk=RiskLevel.LOW)
    b = Taskbot(id="2", name="Baja Clientes", purpose="borrar", apps=(),
                interactions=(I.API,), frequency="d", risk=RiskLevel.LOW)
    assert 0.0 <= sim.score(a, b) <= 100.0


def test_similarity_fit_sin_bots():
    sim = RapidFuzzSimilarity()
    sim.fit([])
    assert sim._hub_apps == set()


def test_similarity_apps_no_hub_distintas():
    from taskbot_advisor.domain.entities import Taskbot
    sim = RapidFuzzSimilarity()
    a = Taskbot(id="1", name="Bot Uno", purpose="x", apps=("Concur",),
                interactions=(I.API,), frequency="d", risk=RiskLevel.LOW)
    b = Taskbot(id="2", name="Bot Dos", purpose="y", apps=("TMS",),
                interactions=(I.API,), frequency="d", risk=RiskLevel.LOW)
    # apps distintas (no vacias) ejercen la rama de division del indice de Jaccard.
    assert 0.0 <= sim.score(a, b) <= 100.0


def test_declares_nombre_sin_tokens_significativos():
    # b.name sin tokens >2 chars y no contenido en la evidencia -> False.
    from taskbot_advisor.domain.entities import Taskbot
    from taskbot_advisor.infrastructure.similarity_rapidfuzz import _declares
    a = Taskbot(id="1", name="Alfa", purpose="", apps=(), interactions=(I.API,),
                frequency="d", risk=RiskLevel.LOW, known_similarity="algo distinto")
    b = Taskbot(id="2", name="Xy", purpose="", apps=(), interactions=(I.API,),
                frequency="d", risk=RiskLevel.LOW)
    assert _declares(a, b) is False


def test_import_main_module():
    import importlib
    mod = importlib.import_module("taskbot_advisor.__main__")
    assert hasattr(mod, "app")


def test_api_enablement_dict_none():
    from taskbot_advisor.infrastructure.renderers.json_renderer import _api_enablement_dict
    assert _api_enablement_dict(None) is None
