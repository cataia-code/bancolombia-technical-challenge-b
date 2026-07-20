# PoC — Taskbot Migration Advisor

Servicio ejecutable de la Parte B: recibe un inventario de taskbots y genera recomendaciones de
consolidación y migración. Arquitectura **hexagonal** (dominio puro + puertos/adapters), CLI y API
para n8n, 82 pruebas con **100% de cobertura**.

## Requisitos

- Python 3.10+ (validado en 3.10.11). Opcional: Docker Compose para el stack con n8n.

## Instalación

```bash
# Desde poc/
python -m pip install -e ".[dev]"
# o solo runtime:
python -m pip install -r requirements.txt
```

## Ejecución (CLI)

```bash
# Con el paquete instalado:
taskbot-advisor analyze data/ejemplo_50_taskbots_prueba.txt

# Sin instalar, apuntando al código fuente:
PYTHONPATH=src python -m taskbot_advisor analyze data/ejemplo_50_taskbots_prueba.txt
```

Genera `reports/<run_id>/reporte.json` y `reporte.html`. En PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m taskbot_advisor analyze data/ejemplo_50_taskbots_prueba.txt
```

## Ejecución (API + n8n)

```bash
docker compose up --build
# API   → http://localhost:8000  (/health, /analyze, /analyze/inline)
# n8n   → http://localhost:5678  → Import → n8n/workflow.json
```

## Pruebas

```bash
python -m pytest                                                   # 82 pruebas
python -m pytest --cov=taskbot_advisor --cov-report=term-missing   # 100% (fail_under=100)
```

Evidencia: [`../docs/evidencia_pruebas.txt`](../docs/evidencia_pruebas.txt).

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `TASKBOT_SIMILARITY_THRESHOLD` | `82` | Umbral [0-100] para tratar dos taskbots como variantes. |
| `TASKBOT_APPS_OVERLAP_WEIGHT` | `0.35` | Peso del solapamiento de apps vs. similitud textual. |
| `TASKBOT_REPORTS_DIR` | `reports` | Carpeta de salida (subcarpeta por `run_id`). |
| `TASKBOT_LLM_ENABLED` | `false` | Habilita la capa de agente LLM (opcional). |
| `ANTHROPIC_API_KEY` | — | Credencial del LLM. Si falta, se usa el advisor determinista. |

## Estructura

```
src/taskbot_advisor/
  domain/          entities, rules, scoring, similarity (pure, no I/O)
  application/     AnalyzeInventory use case + ports
  infrastructure/  repos (csv/json/sqlite/txt), similarity, advisor, renderers, config, logging
  interface/       CLI (Typer) + API (FastAPI for n8n)
data/              real inventory (.txt) + sample (.csv)
n8n/               workflow.json (local) + workflow.cloud.json (self-contained demo) + guide
reports/example/   committed sample report (JSON + HTML)
tests/             unit/ + integration/
```

## Rollback / recuperación

El servicio es *stateless* y de solo lectura sobre el inventario. Corridas idempotentes versionadas
por `run_id` en `reports/<run_id>/` (sin sobrescribir). Fail-soft por ítem; fail-fast en config
inválida; reintentos en el nodo HTTP de n8n. Recuperarse ante fallo = volver a ejecutar.
