"""HTML renderer: human-readable report (business, architecture, operations)."""

from __future__ import annotations

from importlib.resources import files

from jinja2 import Environment

from ...domain.entities import AnalysisResult, MigrationTarget, ReviewStrategy, Wave
from .json_renderer import JsonRenderer

_TARGET_ES = {
    MigrationTarget.N8N: "n8n",
    MigrationTarget.MICROSERVICE: "Microservicio compartido",
    MigrationTarget.CUSTOM_PYTHON_JAVA: "Python/Java a la medida",
    MigrationTarget.RPA_SELECTIVE: "RPA selectivo",
    MigrationTarget.MANUAL_REVIEW: "Revision manual",
}

_REVIEW_ES = {
    ReviewStrategy.NONE: "Sin revision",
    ReviewStrategy.AI_PRECHECK: "Prechequeo IA",
    ReviewStrategy.TARGETED_APPROVAL: "Aprobacion dirigida",
    ReviewStrategy.MANUAL_DEEP_DIVE: "Manual profunda",
}


class HtmlRenderer:
    extension = "html"

    def __init__(self) -> None:
        template_text = (
            files("taskbot_advisor.infrastructure.renderers")
            .joinpath("templates/report.html")
            .read_text(encoding="utf-8")
        )
        self._template = Environment(autoescape=True).from_string(template_text)

    def render(self, result: AnalysisResult) -> str:
        data = JsonRenderer.to_dict(result)
        return self._template.render(
            data=data,
            headlines=_build_headlines(result),
            review_explanation=_build_review_explanation(result),
            wave_3_explanation=_build_wave_3_explanation(result),
            target_label=lambda v: _TARGET_ES[MigrationTarget(v)],
            review_label=lambda v: _REVIEW_ES[ReviewStrategy(v)],
            recommendations=result.recommendations,
            target_of=lambda r: _TARGET_ES[r.target],
        )


def _build_headlines(result: AnalysisResult) -> list[str]:
    """Build the demo-style conclusion sentences from the real data."""
    lines: list[str] = []
    groups = result.consolidation_groups
    if groups:
        total_variants = sum(c.size for c in groups)
        lines.append(
            f"{total_variants} taskbots son variantes de "
            f"{len(groups)} utilidades reutilizables."
        )
    n8n = result.by_target(MigrationTarget.N8N)
    if n8n:
        lines.append(f"{len(n8n)} casos son candidatos a n8n por ser integracion API/archivo/email.")
    rpa = result.by_target(MigrationTarget.RPA_SELECTIVE)
    if rpa:
        lines.append(f"{len(rpa)} deben quedar en RPA selectivo porque dependen de UI legacy.")
    micro = result.by_target(MigrationTarget.MICROSERVICE)
    if micro:
        lines.append(f"{len(micro)} deberian convertirse en un microservicio/componente compartido.")
    wave_1 = result.by_wave(Wave.WAVE_1)
    if wave_1:
        lines.append(f"{len(wave_1)} entran en ola 1 por alto valor y baja complejidad.")
    ai_assisted = sum(1 for r in result.recommendations if r.ai_assisted_review)
    manual_deep = sum(1 for r in result.recommendations if r.needs_manual_review)
    if ai_assisted or manual_deep:
        lines.append(
            f"{ai_assisted} gates se reducen con IA/aprobacion dirigida; "
            f"{manual_deep} requieren evaluacion manual profunda."
        )
    return lines


def _build_review_explanation(result: AnalysisResult) -> list[str]:
    """Explain how the review effort is reduced without removing governance."""
    ai_precheck = sum(
        1 for r in result.recommendations if r.review_strategy is ReviewStrategy.AI_PRECHECK
    )
    targeted = sum(
        1 for r in result.recommendations if r.review_strategy is ReviewStrategy.TARGETED_APPROVAL
    )
    manual_deep = sum(1 for r in result.recommendations if r.needs_manual_review)
    items = [
        (
            f"{ai_precheck} casos tienen API o patron repetible: el agente prepara "
            "evidence pack, controles y checklist antes de implementacion."
            if ai_precheck
            else ""
        ),
        (
            f"{targeted} casos quedan con aprobacion dirigida: IA arma mapa de "
            "dependencias y arquitectura revisa solo el bloqueo especifico."
            if targeted
            else ""
        ),
        (
            f"{manual_deep} casos quedan como evaluacion manual profunda por "
            "complejidad extrema o interaccion no clasificable."
            if manual_deep
            else ""
        ),
    ]
    return [item for item in items if item]


def _build_wave_3_explanation(result: AnalysisResult) -> list[str]:
    """Explain why work lands in Wave 3 instead of presenting it as a bare count."""
    wave_3 = result.by_wave(Wave.WAVE_3)
    extreme_complexity = sum(1 for r in wave_3 if r.complexity_score > 85)
    low_value = sum(1 for r in wave_3 if r.complexity_score <= 85 and r.value_score < 50)
    manual_deep = sum(1 for r in wave_3 if r.needs_manual_review)
    ai_assisted = sum(1 for r in wave_3 if r.ai_assisted_review)
    residual = len(wave_3) - extreme_complexity - low_value
    items = [
        (
            f"{extreme_complexity} tienen complejidad extrema y requieren "
            "redisenio o habilitacion antes de migrar."
            if extreme_complexity
            else ""
        ),
        (
            f"{low_value} quedan por menor valor relativo frente al esfuerzo."
            if low_value
            else ""
        ),
        (
            f"{residual} quedan por combinaciones no prioritarias de valor, "
            "complejidad y dependencias."
            if residual
            else ""
        ),
        (
            f"{manual_deep} requieren evaluacion manual profunda; "
            f"{ai_assisted} quedan con prechequeo IA o aprobacion dirigida."
            if manual_deep or ai_assisted
            else ""
        ),
    ]
    return [item for item in items if item]
