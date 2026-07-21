"""JSON renderer: machine-readable output (for n8n or other consumers).

Output keys stay in Spanish to match the report audience and the HTML renderer.
"""

from __future__ import annotations

import json

from ...domain.entities import (
    AnalysisResult,
    ApiEnablement,
    EvidencePack,
    MigrationTarget,
    ReviewStrategy,
)


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
                "revision": _review_summary(result),
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
            "sensitivity": result.sensitivity,
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
                    "tipo_revision": r.review_strategy.value,
                    "requiere_gate_gobierno": r.requires_governance_gate,
                    "revision_asistida_ia": r.ai_assisted_review,
                    "accion_revision": r.review_action,
                    "evidence_pack": _evidence_pack_dict(r.evidence_pack),
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


def _api_enablement_dict(api: ApiEnablement | None) -> dict | None:
    if api is None:
        return None
    return {
        "sistemas": list(api.systems),
        "api_disponible": api.api_available,
        "api_requerida": api.api_required,
        "bloqueador": api.blocker,
        "accion_habilitadora": api.enabling_action,
        "destino_objetivo_post_habilitacion": api.target_after_enablement.value,
    }


def _evidence_pack_dict(pack: EvidencePack) -> dict:
    return {
        "dependencias": list(pack.dependencies),
        "controles": list(pack.controls),
        "checklist": list(pack.checklist),
        "owner_sugerido": pack.suggested_owner,
        "bloqueadores": list(pack.blockers),
        "siguiente_accion": pack.next_action,
    }


def _review_summary(result: AnalysisResult) -> dict:
    counts = {strategy.value: 0 for strategy in ReviewStrategy}
    for rec in result.recommendations:
        counts[rec.review_strategy.value] += 1
    return {
        **counts,
        "gate_gobierno": sum(1 for rec in result.recommendations if rec.requires_governance_gate),
        "asistida_ia": sum(1 for rec in result.recommendations if rec.ai_assisted_review),
        "manual_profunda": counts[ReviewStrategy.MANUAL_DEEP_DIVE.value],
    }
