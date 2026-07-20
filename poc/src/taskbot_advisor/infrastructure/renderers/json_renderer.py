"""JSON renderer: machine-readable output (for n8n or other consumers).

Output keys stay in Spanish to match the report audience and the HTML renderer.
"""

from __future__ import annotations

import json

from ...domain.entities import AnalysisResult, MigrationTarget


class JsonRenderer:
    extension = "json"

    def render(self, result: AnalysisResult) -> str:
        return json.dumps(self.to_dict(result), ensure_ascii=False, indent=2)

    @staticmethod
    def to_dict(result: AnalysisResult) -> dict:
        return {
            "run_id": result.run_id,
            "summary": {
                "total_taskbots": result.total,
                "grupos_consolidables": len(result.consolidation_groups),
                "por_destino": {
                    t.value: len(result.by_target(t)) for t in MigrationTarget
                },
                "por_ola": {
                    "ola_1": len(result.by_wave(_w("ola_1"))),
                    "ola_2": len(result.by_wave(_w("ola_2"))),
                    "ola_3": len(result.by_wave(_w("ola_3"))),
                },
                "errores": len(result.errors),
            },
            "clusters": [
                {
                    "id": c.id,
                    "miembros": list(c.member_ids),
                    "representante": c.representative_id,
                    "es_grupo_consolidable": c.is_duplicate_group,
                }
                for c in result.clusters
            ],
            "component_candidates": [
                {
                    "cluster_id": c.cluster_id,
                    "nombre_sugerido": c.suggested_name,
                    "miembros": list(c.member_ids),
                    "nombres": list(c.member_names),
                    "proposito_comun": c.common_purpose,
                    "patron_destino": c.target_pattern.value,
                    "apps_dominantes": list(c.dominant_apps),
                    "blocker_legacy": c.legacy_blocker,
                    "requiere_habilitacion_api": c.needs_api_enablement,
                    "accion_recomendada": c.recommended_action,
                }
                for c in result.component_candidates
            ],
            "api_matrix": result.api_matrix,
            "recommendations": [
                {
                    "taskbot_id": r.taskbot_id,
                    "taskbot": r.taskbot_name,
                    "destino": r.target.value,
                    "ola": r.wave.value,
                    "valor": r.value_score,
                    "complejidad": r.complexity_score,
                    "cluster_id": r.cluster_id,
                    "revision_manual": r.needs_manual_review,
                    "razones": r.reasons,
                    "justificacion": r.rationale,
                    "score_breakdown": r.score_breakdown,
                    "api_enablement": _api_enablement_dict(r.api_enablement),
                }
                for r in result.recommendations
            ],
            "errors": result.errors,
        }


def _w(value: str):
    from ...domain.entities import Wave

    return Wave(value)


def _api_enablement_dict(api) -> dict | None:
    if api is None:
        return None
    return {
        "sistemas": list(api.systems),
        "api_disponible": api.api_available,
        "api_requerida": api.api_required,
        "bloqueador": api.blocker,
        "accion_habilitadora": api.enabling_action,
    }
