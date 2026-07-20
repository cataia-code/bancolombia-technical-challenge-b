"""API/no-API assessment per operation (aligned with the Part A capability matrix).

For each recommendation we describe whether an API is available on the systems it
touches, whether the target requires one, what blocks it and the enabling action.
This turns "72% is legacy -> RPA" into a defensible plan (expose APIs to enable
future migration) instead of resignation to RPA.
"""

from __future__ import annotations

from .entities import ApiEnablement, InteractionType, MigrationTarget, Taskbot

# Targets that fundamentally need an API/integration surface to work.
_API_REQUIRED_TARGETS = {MigrationTarget.N8N, MigrationTarget.MICROSERVICE}


def assess(bot: Taskbot, target: MigrationTarget) -> ApiEnablement:
    """Build the API-enablement view for one taskbot given its decided target."""
    api_available = bot.has(InteractionType.API)
    legacy = bot.has(InteractionType.UI_LEGACY)
    database = bot.has(InteractionType.DATABASE)
    api_required = target in _API_REQUIRED_TARGETS or legacy

    if legacy and not api_available:
        blocker = "ui_legacy"
        action = (
            "Exponer una API para el/los sistema(s) legacy; habilita migrar fuera de "
            "RPA en una ola posterior."
        )
    elif database and not api_available:
        blocker = "database"
        action = "Encapsular el acceso a datos tras un servicio/API a la medida."
    elif api_available:
        blocker = None
        action = "Usar la API existente del sistema (sin trabajo de habilitacion)."
    else:
        blocker = None
        action = "Evaluar disponibilidad de API antes de migrar."

    return ApiEnablement(
        systems=bot.apps,
        api_available=api_available,
        api_required=api_required,
        blocker=blocker,
        enabling_action=action,
    )


def system_matrix(bots: list[Taskbot]) -> list[dict]:
    """Aggregate an API/no-API matrix by target system across the portfolio.

    For each application/system: how many taskbots touch it, whether any exposes
    an API, and whether it needs API enablement (touched by a legacy operation
    with no API available on it).
    """
    rows: dict[str, dict] = {}
    for bot in bots:
        api = bot.has(InteractionType.API)
        legacy = bot.has(InteractionType.UI_LEGACY)
        for app in bot.apps:
            row = rows.setdefault(
                app, {"sistema": app, "taskbots": 0, "api_disponible": False,
                       "tocado_por_legacy": False}
            )
            row["taskbots"] += 1
            row["api_disponible"] = row["api_disponible"] or api
            row["tocado_por_legacy"] = row["tocado_por_legacy"] or legacy
    for row in rows.values():
        row["requiere_habilitacion_api"] = (
            row["tocado_por_legacy"] and not row["api_disponible"]
        )
    return sorted(rows.values(), key=lambda r: (-r["taskbots"], r["sistema"]))
