# Prueba Técnica B · Bancolombia — Agente de migración de taskbots

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-live-brightgreen?logo=github)](https://cataia-code.github.io/-bancolombia-technical-challenge-b/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Bancolombia](https://img.shields.io/badge/Bancolombia-Prueba_Técnica_B-FFDA00?labelColor=00317D)](https://www.bancolombia.com/personas)

Solución para la **Parte B** del reto de Senior Software Engineer: un **agente de inteligencia**
que recibe un inventario fragmentado de taskbots (RPA) y produce **decisiones accionables** de
consolidación y migración — qué consolidar, a qué destino migrar (n8n / microservicio / Python-Java
/ RPA selectivo), qué requiere gate de gobierno/IA y qué queda en revisión manual profunda. Todo **local y
reproducible**, sin ambientes ni credenciales del cliente.

> **Sitio publicado:** una vez habilitado GitHub Pages → `https://cataia-code.github.io/-bancolombia-technical-challenge-b/`

Es la implementación local y demostrable del criterio propuesto en la Parte A (el `discovery.py` de
la Ola 0 —Jaccard + union-find + scoring— evoluciona aquí a un servicio hexagonal con destinos,
olas, orquestación n8n y agente).
Para continuidad técnica, `taskbot_advisor.discovery` expone una fachada con nombres compatibles
con la Parte A (`cluster_taskbots`, `priority_score`, `api_matrix`, `run_discovery`) delegando en los
módulos de dominio de B.

---

## Problema que resuelve

Un portafolio de RPA crece de forma fragmentada: taskbots que se duplican, dependen de UI legacy y
mezclan integraciones. Decidir manualmente qué migrar, consolidar o reemplazar es lento y subjetivo.
Esta solución **automatiza el criterio** y lo hace **explicable**:

1. **Racionalizar antes de migrar** — detecta variantes y grupos consolidables.
2. **Orquestar, no bot-izar** — n8n coordina un servicio con API; la lógica vive en el servicio.
3. **Criterio explicable** — reglas deterministas deciden y *justifican*; un agente LLM opcional solo
   redacta, nunca cambia la decisión.

---

## Estructura del proyecto

```text
.
├── docs/                          # Sitio estático (fuente de GitHub Pages)
│   ├── index.html                 # SPA autocontenida (marca Bancolombia, Mermaid, PDF)
│   ├── assets/{images,vendor}/     # Logos Bancolombia + Mermaid empaquetado (sin CDN)
│   ├── diseno.md · uml.md · adr/   # Documento de diseño, UML y 5 ADRs
│   └── evidencia_pruebas.txt       # Evidencia de pruebas
├── poc/                           # Solución ejecutable (arquitectura hexagonal)
│   ├── src/taskbot_advisor/        # domain · application · infrastructure · interface
│   ├── tests/                      # suite unit + integración
│   ├── data/                       # inventario real (.txt) + ejemplo (.csv)
│   ├── n8n/                        # workflow local + guía
│   ├── contracts/                  # contrato OpenAPI versionado
│   ├── scripts/                    # utilidades de mantenimiento de la PoC
│   ├── reports/example/            # reporte de ejemplo versionado (JSON + HTML)
│   ├── Dockerfile · docker-compose.yml · pyproject.toml · requirements.txt
│   └── README.md                   # detalle de ejecución de la PoC
├── challenge/
│   ├── parte b prueba senior.pdf   # Enunciado original del reto
│   └── ejemplo_50_taskbots_prueba.txt  # Catálogo de ejemplo provisto
├── scripts/                        # demo local reproducible (bash/PowerShell)
├── .github/workflows/deploy.yml    # CI/CD: tests + verificación + deploy a Pages
└── README.md
```

## Ejecución local paso a paso

Requisitos: **Python 3.10+** y, para la demo con n8n, **Docker Desktop**.

### Opción A: CLI local

```powershell
# 1. Desde la raíz del repo
python -m venv .venv

# 2. Activar entorno
.\.venv\Scripts\Activate.ps1

# 3. Instalar la PoC con dependencias de desarrollo
pip install -e ".\poc[dev]"

# 4. Analizar el inventario real de 50 taskbots
python -m taskbot_advisor analyze poc\data\ejemplo_50_taskbots_prueba.txt --run-id demo

# 5. Revisar la salida
Get-ChildItem poc\reports\demo

# 6. Ejecutar pruebas
python -m pytest poc\tests
```

```bash
# Linux/macOS/Git Bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "./poc[dev]"
python -m taskbot_advisor analyze poc/data/ejemplo_50_taskbots_prueba.txt --run-id demo
ls poc/reports/demo
python -m pytest poc/tests
```

Los reportes quedan en `poc/reports/demo/reporte.json` y `poc/reports/demo/reporte.html`.

### Opción B: API + n8n con Docker

```powershell
# 1. Levantar API + n8n desde la carpeta de la PoC
cd poc
docker compose up --build

# 2. Validar API en otra terminal
Invoke-RestMethod http://localhost:8000/health
```

Después:

1. Abrir `http://localhost:5678`.
2. Importar `n8n/workflow.json`.
3. Ejecutar *Test workflow*.
4. Confirmar que el nodo final devuelve `run_id`, `headlines`, `resumen`, `revision`,
   `destinos_objetivo_post_habilitacion`, `sensibilidad` y `ola_3`.
5. Revisar el reporte generado en `poc/reports/<run_id>/`.

El stack usa `n8nio/n8n:2.30.5` y el workflow llama al servicio por la red interna de Compose
(`http://advisor:8000/analyze`). CI ejecuta un smoke Docker que levanta ambos servicios, valida
health, importa el workflow local y ejecuta `n8n execute` por ID.

### Sitio local

```powershell
python -m http.server 8080 --directory docs
```

Abrir `http://localhost:8080`.

## Salida (ejemplo, inventario real de 50 taskbots)

```json
{ "total_taskbots": 50, "grupos_consolidables": 15,
  "por_destino": { "n8n": 8, "microservice": 1, "custom_python_java": 5, "rpa_selective": 36 },
  "por_ola": { "ola_1": 7, "ola_2": 29, "ola_3": 14 },
  "revision": { "gate_gobierno": 27, "asistida_ia": 19, "manual_profunda": 8 } }
```

**Por qué 14 quedan en Ola 3:** 8 tienen complejidad extrema y requieren rediseño o habilitación
antes de migrar; 6 quedan por menor valor relativo frente al esfuerzo. Además, los 27 gates de
gobierno ya no se tratan como revisión manual completa: 19 pasan por prechequeo IA / aprobación
dirigida y solo 8 quedan como evaluación manual profunda.

Reporte de ejemplo versionado en [`poc/reports/example/`](poc/reports/example/) (JSON + HTML).

## Orquestación con n8n

`cd poc && docker compose up --build` levanta n8n (`:5678`) + el servicio (`:8000`). Importar
`poc/n8n/workflow.json` y ejecutar *Test workflow*. Detalle en
[`poc/n8n/README-n8n.md`](poc/n8n/README-n8n.md).

## Plan de racionalización (salida enriquecida)

Además de la recomendación por taskbot, el reporte produce:
- **Catálogo de componentes reutilizables** (`component_candidates`): nombre sugerido, miembros,
  propósito común, patrón destino, apps dominantes, blocker legacy y acción recomendada.
- **Matriz API/no-API** por sistema (`api_matrix`) y por operación (`api_enablement`): qué requiere
  *API enablement* para migrar fuera de RPA, incluido `destino_objetivo_post_habilitacion`.
- **Política de revisión** (`summary.revision`, `tipo_revision`, `accion_revision`): separa gate de
  gobierno, prechequeo IA, aprobación dirigida y evaluación manual profunda.
- **Evidence pack** (`evidence_pack`): dependencias, controles, checklist, owner sugerido,
  bloqueadores y siguiente acción para que la intervención IA sea auditable.
- **Sensibilidad de umbrales** (`sensitivity`): recalcula gates/manual profunda y olas bajo escenarios
  de complejidad `80/85/90` y dependencias `3/4`.
- **Scoring explicado** (`score_breakdown`) por recomendación: frecuencia, riesgo, duplicidad,
  complejidad por interacción y dependencias.

## Documentación

- [Sitio web técnico](docs/index.html) — misma identidad visual que la Parte A.
- [Documento de diseño](docs/diseno.md) · [UML](docs/uml.md) · [ADRs](docs/adr/) · [Resumen ejecutivo](docs/resumen_ejecutivo.md) · [Runbook de demo/fallo](docs/runbook.md)
- Contrato: [`poc/contracts/openapi.json`](poc/contracts/openapi.json) (validado en CI).

## Decisiones clave

- **Arquitectura hexagonal ligera**: núcleo de negocio puro y testeable; orillas intercambiables. ([ADR-001](docs/adr/ADR-001-arquitectura-hexagonal.md))
- **Motor híbrido con fallback**: reglas deterministas deciden (reproducible, offline); LLM opcional solo enriquece. ([ADR-004](docs/adr/ADR-004-agente-hibrido-fallback.md))
- **Similitud multi-señal**: evidencia declarada + apps no-hub + texto, evita el encadenamiento single-linkage. ([ADR-003](docs/adr/ADR-003-similitud-multisenal.md))

## Rollback / recuperación ante fallo

Servicio *stateless* y de solo lectura sobre el inventario. Cada corrida es **idempotente y
versionada por `run_id`** (`reports/<run_id>/`, sin sobrescribir). Fail-soft por ítem; fail-fast en
configuración inválida; el nodo HTTP de n8n reintenta. Recuperarse = volver a ejecutar.
