"""HTML renderer: human-readable report (business, architecture, operations)."""

from __future__ import annotations

from importlib.resources import files

from jinja2 import Environment

from ...domain.entities import AnalysisResult, MigrationTarget, Wave
from .json_renderer import JsonRenderer

_TARGET_ES = {
    MigrationTarget.N8N: "n8n",
    MigrationTarget.MICROSERVICE: "Microservicio compartido",
    MigrationTarget.CUSTOM_PYTHON_JAVA: "Python/Java a la medida",
    MigrationTarget.RPA_SELECTIVE: "RPA selectivo",
    MigrationTarget.MANUAL_REVIEW: "Revision manual",
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
            target_label=lambda v: _TARGET_ES[MigrationTarget(v)],
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
    return lines
