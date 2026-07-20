"""CLI interface (Typer). Human entry point and for local automations.

It holds no business logic: it only translates command-line arguments into a use
case invocation and presents the result (Separation of Concerns). User-facing
messages stay in Spanish.
"""

from __future__ import annotations

import json

import typer

from ..infrastructure.config import Settings
from ..infrastructure.container import build_use_case, write_reports
from ..infrastructure.renderers.json_renderer import JsonRenderer

app = typer.Typer(add_completion=False, help="Agente de consolidacion/migracion de taskbots.")


@app.callback()
def _main() -> None:
    """Agente de consolidacion y priorizacion de migracion de taskbots."""
    # Forces Typer to expose 'analyze' as an explicit subcommand.


@app.command()
def analyze(
    inventory: str = typer.Argument(..., help="Ruta al inventario (.csv, .json o .sqlite)."),
    run_id: str = typer.Option(None, help="Identificador de corrida (por defecto se genera)."),
    quiet: bool = typer.Option(False, help="No imprimir el resumen legible."),
) -> None:
    """Analyze an inventory and write JSON + HTML reports to reports/<run_id>/."""
    settings = Settings.from_env()
    result = build_use_case(inventory, settings).execute(run_id=run_id)
    paths = write_reports(result, settings)

    if not quiet:
        summary = JsonRenderer.to_dict(result)["summary"]
        typer.echo(f"run_id: {result.run_id}")
        typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        typer.echo(f"Reportes: {paths['json']}  |  {paths['html']}")


if __name__ == "__main__":  # pragma: no cover
    app()
