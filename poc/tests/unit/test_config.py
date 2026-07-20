"""Tests de configuracion: defaults, parseo de entorno y fail-fast."""

import pytest

from taskbot_advisor.infrastructure.config import Settings


def test_defaults():
    s = Settings()
    assert s.similarity_threshold == 82.0
    assert s.llm_enabled is False


def test_from_env_defaults(monkeypatch):
    for k in ["TASKBOT_SIMILARITY_THRESHOLD", "TASKBOT_APPS_OVERLAP_WEIGHT",
              "TASKBOT_REPORTS_DIR", "TASKBOT_LLM_ENABLED", "TASKBOT_LLM_MODEL",
              "ANTHROPIC_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env()
    assert s.similarity_threshold == 82.0
    assert s.llm_enabled is False
    assert s.llm_api_key is None


def test_from_env_threshold_invalido_fuera_de_rango(monkeypatch):
    monkeypatch.setenv("TASKBOT_SIMILARITY_THRESHOLD", "150")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_from_env_threshold_no_numerico(monkeypatch):
    monkeypatch.setenv("TASKBOT_SIMILARITY_THRESHOLD", "abc")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_from_env_llm_requiere_credencial(monkeypatch):
    # Habilitado pero SIN key -> queda deshabilitado (nunca depende del LLM).
    monkeypatch.setenv("TASKBOT_LLM_ENABLED", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert Settings.from_env().llm_enabled is False


def test_from_env_llm_habilitado_con_key(monkeypatch):
    monkeypatch.setenv("TASKBOT_LLM_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings.from_env()
    assert s.llm_enabled is True
    assert s.llm_api_key == "sk-test"
