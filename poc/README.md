# PoC — Taskbot Migration Advisor

Servicio ejecutable de la Parte B: recibe un inventario de taskbots y genera recomendaciones de
consolidación y migración. Arquitectura **hexagonal** (dominio puro + puertos/adapters), CLI y API
para n8n, con suite automatizada e integración Docker local.

## Requisitos

- Python 3.10+ (validado en 3.10.11). Opcional: Docker Compose para el stack con n8n.

## Ejecución local paso a paso

### 1. Instalar dependencias

```bash
# Desde poc/
python -m pip install -e ".[dev]"
# o solo runtime:
python -m pip install -r requirements.txt
```

### 2. Ejecutar por CLI

```bash
# Con el paquete instalado:
taskbot-advisor analyze data/ejemplo_50_taskbots_prueba.txt --run-id demo

# Sin instalar, apuntando al código fuente:
PYTHONPATH=src python -m taskbot_advisor analyze data/ejemplo_50_taskbots_prueba.txt --run-id demo
```

Genera `reports/demo/reporte.json` y `reports/demo/reporte.html`. En PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m taskbot_advisor analyze data/ejemplo_50_taskbots_prueba.txt --run-id demo
Get-ChildItem reports\demo
```

### 3. Ejecutar API + n8n con Docker

```bash
docker compose up --build
# API   → http://localhost:8000  (/health, /analyze, /analyze/inline)
# n8n   → http://localhost:5678  → Import from File → n8n/workflow.json
```

En otra terminal:

```bash
curl http://localhost:8000/health
```

En n8n: importar `n8n/workflow.json`, ejecutar *Test workflow* y revisar `run_id`, `headlines`,
`resumen`, `revision`, `destinos_objetivo_post_habilitacion`, `sensibilidad` y `ola_3`.
El reporte queda en `reports/<run_id>/`.

## Pruebas

```bash
python -m pytest
```

Evidencia: [`../docs/evidencia_pruebas.txt`](../docs/evidencia_pruebas.txt).

Resultado esperado con el inventario de 50 taskbots: Ola 1 = 7, Ola 2 = 29, Ola 3 = 14. La politica
de revision separa 27 gates de gobierno en 19 casos asistidos por IA/aprobacion dirigida y 8 de
evaluacion manual profunda.
La salida tambien incluye `evidence_pack` por taskbot, `destino_objetivo_post_habilitacion` en
`api_enablement` y `sensitivity` para comparar umbrales de revision.

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `TASKBOT_SIMILARITY_THRESHOLD` | `82` | Umbral [0-100] para tratar dos taskbots como variantes. |
| `TASKBOT_APPS_OVERLAP_WEIGHT` | `0.35` | Peso del solapamiento de apps vs. similitud textual. |
| `TASKBOT_REPORTS_DIR` | `reports` | Carpeta de salida (subcarpeta por `run_id`). |
| `TASKBOT_INVENTORY_ROOT` | — | Si se define, `/analyze` solo acepta inventarios contenidos en esta ruta (guardrail para exposición externa). |
| `TASKBOT_LLM_ENABLED` | `false` | Habilita la capa de agente LLM (opcional). |
| `ANTHROPIC_API_KEY` | — | Credencial del LLM. Si falta, se usa el advisor determinista. |

## Estructura

```
src/taskbot_advisor/
  discovery.py      Part A-compatible facade: cluster_taskbots, priority_score, api_matrix, run_discovery
  domain/          entities, rules, review, scoring, similarity (pure, no I/O)
  application/     AnalyzeInventory use case + ports
  infrastructure/  repos (csv/json/sqlite/txt), similarity, advisor, renderers, config, logging
  interface/       CLI (Typer) + API (FastAPI for n8n)
data/              real inventory (.txt) + sample (.csv)
n8n/               workflow.json (local) + guide
contracts/         committed OpenAPI contract
scripts/           OpenAPI export/check helper
reports/example/   committed sample report (JSON + HTML)
tests/             unit/ + integration/
```

## Rollback / recuperación

El servicio es *stateless* y de solo lectura sobre el inventario. Corridas idempotentes versionadas
por `run_id` en `reports/<run_id>/` (sin sobrescribir). Fail-soft por ítem; fail-fast en config
inválida; reintentos en el nodo HTTP de n8n. Recuperarse ante fallo = volver a ejecutar.
