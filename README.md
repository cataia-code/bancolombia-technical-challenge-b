# Prueba Técnica B · Bancolombia — Agente de migración de taskbots

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-live-brightgreen?logo=github)](https://cataia-code.github.io/-bancolombia-technical-challenge-b/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](docs/evidencia_pruebas.txt)
[![Bancolombia](https://img.shields.io/badge/Bancolombia-Prueba_Técnica_B-FFDA00?labelColor=00317D)](https://www.bancolombia.com/personas)

Solución para la **Parte B** del reto de Senior Software Engineer: un **agente de inteligencia**
que recibe un inventario fragmentado de taskbots (RPA) y produce **decisiones accionables** de
consolidación y migración — qué consolidar, a qué destino migrar (n8n / microservicio / Python-Java
/ RPA selectivo), qué requiere revisión manual y en qué **ola** entra cada caso. Todo **local y
reproducible**, sin ambientes ni credenciales del cliente.

> **Sitio publicado:** una vez habilitado GitHub Pages → `https://cataia-code.github.io/-bancolombia-technical-challenge-b/`

Es la implementación local y demostrable del criterio propuesto en la Parte A (el `discovery.py` de
la Ola 0 —Jaccard + union-find + scoring— evoluciona aquí a un servicio hexagonal con destinos,
olas, orquestación n8n y agente).

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
│   └── evidencia_pruebas.txt       # Salida de pytest + cobertura
├── poc/                           # Solución ejecutable (arquitectura hexagonal)
│   ├── src/taskbot_advisor/        # domain · application · infrastructure · interface
│   ├── tests/                      # 82 tests (unit + integración), 100% cobertura
│   ├── data/                       # inventario real (.txt) + ejemplo (.csv)
│   ├── n8n/                        # workflow local + workflow.cloud.json + guía
│   ├── reports/example/            # reporte de ejemplo versionado (JSON + HTML)
│   ├── Dockerfile · docker-compose.yml · pyproject.toml · requirements.txt
│   └── README.md                   # detalle de ejecución de la PoC
├── challenge/
│   ├── parte b prueba senior.pdf   # Enunciado original del reto
│   └── ejemplo_50_taskbots_prueba.txt  # Catálogo de ejemplo provisto
├── .github/workflows/deploy.yml    # CI/CD: tests 100% + verificación + deploy a Pages
└── README.md
```

## Ejecución local (quickstart)

Requisitos: **Python 3.10+** (validado en 3.10.11) y, opcionalmente, **Docker** para el stack con n8n.

**1. Crear el entorno virtual e instalar dependencias** (una sola vez, desde la raíz):

```powershell
# PowerShell (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\poc[dev]"
```

```bash
# bash (Linux/macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -e "./poc[dev]"
```

**2. Ejecutar la solución y las pruebas** (con la venv activada, desde la raíz):

```bash
# Analiza el inventario real (50 taskbots) -> reports/<run_id>/reporte.json + .html
python -m taskbot_advisor analyze poc/data/ejemplo_50_taskbots_prueba.txt

# Tests con 100% de cobertura (umbral fail_under=100)
python -m pytest poc/tests --cov=taskbot_advisor --cov-report=term-missing

# Sitio: servir en local y abrir http://localhost:8080
python -m http.server 8080 --directory docs
```

> Todos los comandos de la PoC se pueden correr también entrando a `poc/` (donde vive
> `pyproject.toml`). Ver [`poc/README.md`](poc/README.md) para el detalle.

## Salida (ejemplo, inventario real de 50 taskbots)

```json
{ "total_taskbots": 50, "grupos_consolidables": 15,
  "por_destino": { "n8n": 8, "microservice": 1, "custom_python_java": 5, "rpa_selective": 36 },
  "por_ola": { "ola_1": 2, "ola_2": 7, "ola_3": 41 } }
```

Reporte de ejemplo versionado en [`poc/reports/example/`](poc/reports/example/) (JSON + HTML).

## Orquestación con n8n

- **Local:** `cd poc && docker compose up --build` levanta n8n (`:5678`) + el servicio (`:8000`).
  Importar `poc/n8n/workflow.json` → *Test workflow*.
- **n8n Cloud:** importar `poc/n8n/workflow.cloud.json` — workflow **autocontenido** para
  demostración. ⚠️ Duplica las reglas en JavaScript **solo como fallback de demo** (n8n Cloud no
  alcanza `localhost`); la **fuente única de verdad es el servicio Python**. Para producción se usa
  el nodo HTTP contra el servicio (vía túnel público). Detalle en [`poc/n8n/README-n8n.md`](poc/n8n/README-n8n.md).

## Documentación

- [Sitio web técnico](docs/index.html) — misma identidad visual que la Parte A.
- [Documento de diseño](docs/diseno.md) · [UML](docs/uml.md) · [ADRs](docs/adr/) · [Resumen ejecutivo](docs/resumen_ejecutivo.md)

## Decisiones clave

- **Arquitectura hexagonal ligera**: núcleo de negocio puro y testeable; orillas intercambiables. ([ADR-001](docs/adr/ADR-001-arquitectura-hexagonal.md))
- **Motor híbrido con fallback**: reglas deterministas deciden (reproducible, offline); LLM opcional solo enriquece. ([ADR-004](docs/adr/ADR-004-agente-hibrido-fallback.md))
- **Similitud multi-señal**: evidencia declarada + apps no-hub + texto, evita el encadenamiento single-linkage. ([ADR-003](docs/adr/ADR-003-similitud-multisenal.md))

## Rollback / recuperación ante fallo

Servicio *stateless* y de solo lectura sobre el inventario. Cada corrida es **idempotente y
versionada por `run_id`** (`reports/<run_id>/`, sin sobrescribir). Fail-soft por ítem; fail-fast en
configuración inválida; el nodo HTTP de n8n reintenta. Recuperarse = volver a ejecutar.
