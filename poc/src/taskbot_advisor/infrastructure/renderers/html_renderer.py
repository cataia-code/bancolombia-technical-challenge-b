"""HTML renderer: human-readable report (business, architecture, operations).

Uses Jinja2 with an embedded template (self-contained: no external files or
CDN). Reproduces the actionable conclusions the challenge asks to demo live
(variants, n8n candidates, selective RPA, waves). The template text stays in
Spanish (the report audience).
"""

from __future__ import annotations

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
        self._env = Environment(autoescape=True)
        self._template = self._env.from_string(_TEMPLATE)

    def render(self, result: AnalysisResult) -> str:
        data = JsonRenderer.to_dict(result)
        headlines = _build_headlines(result)
        return self._template.render(
            data=data,
            headlines=headlines,
            target_label=lambda v: _TARGET_ES[MigrationTarget(v)],
            recommendations=result.recommendations,
            target_of=lambda r: _TARGET_ES[r.target],
        )


def _build_headlines(result: AnalysisResult) -> list[str]:
    """Build the demo-style conclusion sentences from the real data."""
    lines: list[str] = []
    groups = result.consolidation_groups
    if groups:
        total_variantes = sum(c.size for c in groups)
        lines.append(
            f"{total_variantes} taskbots son variantes de {len(groups)} utilidades reutilizables."
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
    ola1 = result.by_wave(Wave.WAVE_1)
    if ola1:
        lines.append(f"{len(ola1)} entran en ola 1 por alto valor y baja complejidad.")
    return lines


_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte de migracion de taskbots</title>
<style>
 body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}
 .wrap{max-width:1080px;margin:0 auto;padding:32px 20px}
 h1{font-size:1.6rem;margin:0 0 4px} .sub{color:#94a3b8;margin:0 0 24px}
 .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}
 .card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px}
 .card .n{font-size:1.7rem;font-weight:700;color:#38bdf8} .card .l{color:#94a3b8;font-size:.85rem}
 .headlines{background:#132e1f;border:1px solid #14532d;border-radius:10px;padding:16px 20px;margin:20px 0}
 .headlines li{margin:6px 0}
 table{width:100%;border-collapse:collapse;margin-top:12px;font-size:.9rem}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #334155;vertical-align:top}
 th{color:#94a3b8;font-weight:600}
 .tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.75rem;background:#334155}
 .w1{color:#22c55e} .w2{color:#eab308} .w3{color:#f87171}
 code{color:#7dd3fc}
</style></head><body><div class="wrap">
 <h1>Reporte de consolidacion y migracion de taskbots</h1>
 <p class="sub">run_id: <code>{{ data.run_id }}</code> &middot; {{ data.summary.total_taskbots }} taskbots analizados</p>

 <div class="headlines"><strong>Hallazgos accionables</strong>
   <ul>{% for h in headlines %}<li>{{ h }}</li>{% endfor %}</ul>
 </div>

 <div class="cards">
   <div class="card"><div class="n">{{ data.summary.grupos_consolidables }}</div><div class="l">Grupos consolidables</div></div>
   <div class="card"><div class="n w1">{{ data.summary.por_ola.ola_1 }}</div><div class="l">Ola 1 (quick wins)</div></div>
   <div class="card"><div class="n w2">{{ data.summary.por_ola.ola_2 }}</div><div class="l">Ola 2</div></div>
   <div class="card"><div class="n w3">{{ data.summary.por_ola.ola_3 }}</div><div class="l">Ola 3</div></div>
   <div class="card"><div class="n">{{ data.summary.errores }}</div><div class="l">Errores</div></div>
 </div>

 <h2 style="font-size:1.1rem">Distribucion por destino</h2>
 <div class="cards">
 {% for k,v in data.summary.por_destino.items() %}{% if v>0 %}
   <div class="card"><div class="n">{{ v }}</div><div class="l">{{ target_label(k) }}</div></div>
 {% endif %}{% endfor %}
 </div>

 <h2 style="font-size:1.1rem">Recomendaciones por taskbot</h2>
 <table><thead><tr>
   <th>Taskbot</th><th>Destino</th><th>Ola</th><th>Valor</th><th>Compl.</th><th>Justificacion</th>
 </tr></thead><tbody>
 {% for r in recommendations %}
   <tr>
     <td>{{ r.taskbot_name }}{% if r.cluster_id is not none %} <span class="tag">cluster {{ r.cluster_id }}</span>{% endif %}</td>
     <td>{{ target_of(r) }}</td>
     <td class="{{ 'w1' if r.wave.value=='ola_1' else 'w2' if r.wave.value=='ola_2' else 'w3' }}">{{ r.wave.value }}</td>
     <td>{{ r.value_score }}</td><td>{{ r.complexity_score }}</td>
     <td>{{ r.rationale }}</td>
   </tr>
 {% endfor %}
 </tbody></table>

 {% if data.errors %}<h2 style="font-size:1.1rem">Errores ({{ data.errors|length }})</h2>
 <table><tbody>{% for e in data.errors %}<tr><td>{{ e }}</td></tr>{% endfor %}</tbody></table>{% endif %}
</div></body></html>"""
