"""Tests de los advisors (justificacion) y su factory con fallback."""

from taskbot_advisor.domain.entities import (
    InteractionType,
    MigrationTarget,
    Recommendation,
    RiskLevel,
    Taskbot,
    Wave,
)
from taskbot_advisor.infrastructure.advisor import (
    DeterministicAdvisor,
    LlmAdvisor,
    build_advisor,
)
from taskbot_advisor.infrastructure.config import Settings


def _bot():
    return Taskbot(
        id="t1", name="Bot X", purpose="hace algo", apps=("SAP",),
        interactions=(InteractionType.API,), frequency="diaria", risk=RiskLevel.LOW,
    )


def _rec():
    return Recommendation(
        taskbot_id="t1", taskbot_name="Bot X", target=MigrationTarget.N8N, wave=Wave.WAVE_1,
        value_score=70.0, complexity_score=20.0, cluster_id=None,
        reasons=["Integracion API-first: candidato a n8n."],
    )


def test_deterministic_advisor_incluye_destino_y_scores():
    text = DeterministicAdvisor().explain(_bot(), _rec())
    assert "n8n" in text
    assert "70.0" in text and "20.0" in text


def test_deterministic_sin_razones_usa_texto_base():
    rec = _rec()
    rec.reasons = []
    text = DeterministicAdvisor().explain(_bot(), rec)
    assert "reglas base" in text.lower()


def test_build_advisor_sin_llm_es_determinista():
    advisor = build_advisor(Settings(llm_enabled=False))
    assert isinstance(advisor, DeterministicAdvisor)


def test_build_advisor_llm_sin_libreria_cae_a_determinista(monkeypatch):
    # Con llm habilitado + key pero la construccion del cliente falla -> fallback.
    settings = Settings(llm_enabled=True, llm_api_key="sk-x", llm_model="m")
    monkeypatch.setattr(
        "taskbot_advisor.infrastructure.advisor.LlmAdvisor",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no anthropic")),
    )
    assert isinstance(build_advisor(settings), DeterministicAdvisor)


class _FakeBlock:
    type = "text"
    text = "Justificacion redactada por el agente."


class _FakeMsg:
    content = [_FakeBlock()]


class _FakeClient:
    def __init__(self, ok=True):
        self._ok = ok
        self.messages = self

    def create(self, **kw):
        if not self._ok:
            raise RuntimeError("api down")
        return _FakeMsg()


def _make_llm(client):
    advisor = LlmAdvisor.__new__(LlmAdvisor)
    advisor._model = "m"
    advisor._fallback = DeterministicAdvisor()
    advisor._client = client
    return advisor


def test_llm_advisor_usa_respuesta_del_modelo():
    advisor = _make_llm(_FakeClient(ok=True))
    assert advisor.explain(_bot(), _rec()) == "Justificacion redactada por el agente."


def test_llm_advisor_falla_y_cae_a_determinista():
    advisor = _make_llm(_FakeClient(ok=False))
    text = advisor.explain(_bot(), _rec())
    assert "n8n" in text  # vino del fallback determinista


def test_llm_advisor_init_con_libreria_falsa(monkeypatch):
    # Inyecta un modulo 'anthropic' falso para ejercer el __init__ real (import + cliente).
    import sys
    import types

    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda api_key: _FakeClient(ok=True)
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    advisor = LlmAdvisor("sk-x", "modelo-x")
    assert advisor.explain(_bot(), _rec()) == "Justificacion redactada por el agente."
