"""Advisors: write the justification of an already-decided recommendation.

Two implementations of the ``AgentAdvisor`` port:

  - DeterministicAdvisor: composes the justification from the reasons and scores.
    It is the DEFAULT: 100% offline and reproducible.
  - LlmAdvisor: optional; uses an LLM to write a more natural justification. If
    anything fails or there is no credential, it degrades to the deterministic
    one (fallback) so the solution never depends on the LLM.

Neither changes the decision (target/wave): they only produce text. User-facing
strings stay in Spanish (the report audience).
"""

from __future__ import annotations

from ..domain.entities import MigrationTarget, Recommendation, Taskbot

_TARGET_LABEL = {
    MigrationTarget.N8N: "n8n (orquestador de integraciones)",
    MigrationTarget.MICROSERVICE: "microservicio / componente compartido",
    MigrationTarget.CUSTOM_PYTHON_JAVA: "automatizacion a la medida (Python/Java)",
    MigrationTarget.RPA_SELECTIVE: "RPA selectivo",
    MigrationTarget.MANUAL_REVIEW: "revision manual previa",
}


class DeterministicAdvisor:
    """Deterministic justification: always available, always the same."""

    def explain(self, bot: Taskbot, rec: Recommendation) -> str:
        target = _TARGET_LABEL[rec.target]
        cause = " ".join(rec.reasons) if rec.reasons else "Clasificado por reglas base."
        return (
            f"'{bot.name}' se recomienda para {target} (ola {rec.wave.value.split('_')[-1]}). "
            f"{cause} "
            f"Valor={rec.value_score}, complejidad={rec.complexity_score}."
        )


class LlmAdvisor:
    """Optional LLM-assisted advisor, with fallback to the deterministic one.

    It is only instantiated when a credential exists and it is enabled. The
    prompt forces the model to EXPLAIN the already-taken decision, not to re-decide.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._fallback = DeterministicAdvisor()
        # Lazy import: the LLM library is an optional dependency.
        from anthropic import Anthropic  # noqa: PLC0415

        self._client = Anthropic(api_key=api_key)

    def explain(self, bot: Taskbot, rec: Recommendation) -> str:
        prompt = _build_prompt(bot, rec)
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=180,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in msg.content if block.type == "text").strip()
            return text or self._fallback.explain(bot, rec)
        except Exception:
            # Any LLM failure (network, quota, credential) -> clean fallback.
            return self._fallback.explain(bot, rec)


def _build_prompt(bot: Taskbot, rec: Recommendation) -> str:
    return (
        "Eres un arquitecto de automatizacion. Explica en 2 frases, claras para "
        "negocio y arquitectura, POR QUE este taskbot recibe la siguiente decision "
        "(NO cambies la decision, solo justificala):\n"
        f"- Taskbot: {bot.name} | proposito: {bot.purpose}\n"
        f"- Interaccion: {', '.join(i.value for i in bot.interactions)} | apps: {', '.join(bot.apps)}\n"
        f"- Destino: {rec.target.value} | Ola: {rec.wave.value}\n"
        f"- Razones internas: {'; '.join(rec.reasons)}\n"
        f"- Valor={rec.value_score}, Complejidad={rec.complexity_score}"
    )


def build_advisor(settings) -> object:
    """Factory: LLM if enabled and credentialed; otherwise deterministic."""
    if settings.llm_enabled and settings.llm_api_key:
        try:
            return LlmAdvisor(settings.llm_api_key, settings.llm_model)
        except Exception:
            return DeterministicAdvisor()  # e.g. 'anthropic' library not installed
    return DeterministicAdvisor()
