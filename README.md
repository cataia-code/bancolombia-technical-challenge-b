# Prueba Tecnica B - Taskbot Migration Advisor

Solucion local para clasificar un inventario de taskbots RPA y producir un plan de consolidacion y
migracion. La logica decide destino, ola, revision requerida, evidence pack, sensibilidad de
umbrales y destino objetivo despues de habilitar APIs.

La solucion es reproducible sin ambientes del cliente: corre por CLI, API FastAPI y workflow local
de n8n en Docker.

## Resultado con 50 taskbots

| Vista | Resultado |
|---|---|
| Destino | n8n: 8, microservice: 1, custom Python/Java: 5, RPA selectivo: 36 |
| Olas | Ola 1: 7, Ola 2: 29, Ola 3: 14 |
| Revision | Sin revision: 23, prechequeo IA: 13, aprobacion dirigida: 6, manual profunda: 8 |
| Consolidacion | 15 grupos consolidables |

Taskbots por ola:

- Ola 1: `TB13, TB26, TB27, TB28, TB38, TB43, TB47`
- Ola 2: `TB01, TB04, TB05, TB06, TB07, TB09, TB10, TB11, TB14, TB17, TB18, TB19, TB20, TB21, TB22, TB24, TB25, TB29, TB31, TB34, TB35, TB36, TB40, TB41, TB42, TB44, TB46, TB48, TB49`
- Ola 3: `TB02, TB03, TB08, TB12, TB15, TB16, TB23, TB30, TB32, TB33, TB37, TB39, TB45, TB50`

## Estructura minima

```text
.
├── docs/
│   ├── index.html              # sitio publicado en GitHub Pages
│   ├── architecture.md         # diseno, decisiones y diagramas resumidos
│   ├── evidencia_pruebas.txt   # evidencia de validacion local
│   └── assets/                 # logo y Mermaid local para el sitio
├── poc/
│   ├── src/taskbot_advisor/    # domain, application, infrastructure, interface
│   ├── tests/                  # unit + integration
│   ├── data/                   # inventarios de ejemplo
│   ├── n8n/workflow.json       # workflow local
│   ├── contracts/              # OpenAPI versionado
│   ├── reports/example/        # reporte de referencia
│   └── docker-compose.yml
└── .github/workflows/deploy.yml
```

## Ejecucion local con Python

Requisitos: Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\poc[dev]"
python -m taskbot_advisor analyze poc\data\ejemplo_50_taskbots_prueba.txt --run-id demo
python -m pytest poc\tests
```

Los reportes quedan en `poc/reports/demo/reporte.json` y `poc/reports/demo/reporte.html`.

## Ejecucion local con Docker + n8n

```powershell
docker compose -f poc\docker-compose.yml up -d --build
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:5678/healthz
```

n8n queda en `http://localhost:5678`. Importar `poc/n8n/workflow.json` y ejecutar el workflow.
El nodo final devuelve `run_id`, `headlines`, `resumen`, `revision`,
`destinos_objetivo_post_habilitacion`, `sensibilidad` y `ola_3`.

Smoke tecnico sin UI:

```powershell
docker compose -f poc\docker-compose.yml run --rm --no-deps --entrypoint /bin/sh n8n /home/node/.n8n-import/smoke.sh
```

## API

```powershell
$body = '{"inventory_path":"ejemplo_50_taskbots_prueba.txt","persist":false}'
Invoke-RestMethod -Method Post http://localhost:8000/analyze -ContentType 'application/json' -Body $body
```

Endpoints principales:

- `GET /health`
- `POST /analyze`
- `POST /analyze/inline`

Contrato: `poc/contracts/openapi.json`.

## Documentacion

- Sitio tecnico: `docs/index.html`
- Diseno y diagramas resumidos: `docs/architecture.md`
- Evidencia de pruebas: `docs/evidencia_pruebas.txt`

## Decisiones clave

- Monolito modular con arquitectura hexagonal ligera.
- Reglas deterministas deciden; el agente LLM opcional solo enriquece texto y tiene fallback.
- n8n orquesta por HTTP; la logica de negocio vive en el servicio.
- La fachada `taskbot_advisor.discovery` mantiene nombres compatibles con la Parte A:
  `cluster_taskbots`, `priority_score`, `api_matrix` y `run_discovery`.
