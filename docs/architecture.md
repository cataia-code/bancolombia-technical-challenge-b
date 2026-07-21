# Arquitectura y decisiones

Documento compacto de diseno. Resume arquitectura, reglas y diagramas; los registros formales de
decision se conservan en `docs/adr/` para trazabilidad ante evaluacion.

## Objetivo

Clasificar taskbots RPA en un plan accionable:

- consolidar variantes,
- elegir destino tecnologico (`n8n`, `microservice`, `custom_python_java`, `rpa_selective`),
- priorizar por ola,
- separar revision asistida de revision manual profunda,
- explicar cada decision con evidencia auditable.

## Arquitectura

La solucion usa un monolito modular con arquitectura hexagonal ligera.

```text
interface      CLI Typer, FastAPI
application    AnalyzeInventory + ports
domain         entities, rules, review, scoring, similarity, api_enablement
infrastructure repositories, renderers, config, logging, advisor, RapidFuzz
```

El dominio no hace I/O. El caso de uso depende de puertos, y los adaptadores viven en
`infrastructure`. Esto mantiene las reglas testeables y permite cambiar fuente de inventario,
renderers u orquestador sin tocar el nucleo.

## Flujo principal

```mermaid
sequenceDiagram
    participant U as CLI / n8n
    participant UC as AnalyzeInventory
    participant R as InventoryRepository
    participant S as SimilarityScorer
    participant D as Domain
    participant A as AgentAdvisor
    participant W as Renderers

    U->>UC: execute(run_id)
    UC->>R: load()
    R-->>UC: taskbots, errors
    opt scorer trainable
        UC->>S: fit(taskbots)
    end
    UC->>D: build_clusters(taskbots)
    loop each taskbot
        UC->>D: classify + review + score + api_enablement
        D-->>UC: recommendation
        UC->>A: explain(bot, recommendation)
    end
    UC->>D: components + API matrix + threshold sensitivity
    UC-->>U: AnalysisResult
    U->>W: JSON + HTML report
```

## Modelo resumido

```mermaid
classDiagram
    class Taskbot {
      +id: str
      +name: str
      +purpose: str
      +apps: tuple
      +interactions: tuple
      +risk: RiskLevel
      +dependencies: tuple
      +normalized_text() str
      +has(interaction) bool
    }
    class Recommendation {
      +taskbot_id: str
      +target: MigrationTarget
      +wave: Wave
      +value_score: float
      +complexity_score: float
      +review_strategy: ReviewStrategy
      +evidence_pack: EvidencePack
      +api_enablement: ApiEnablement
    }
    class ReviewPlan {
      +strategy: ReviewStrategy
      +reason: str
      +action: str
      +evidence_pack: EvidencePack
      +requires_governance_gate: bool
      +is_ai_assisted: bool
      +needs_manual_review: bool
    }
    class EvidencePack {
      +dependencies: tuple
      +controls: tuple
      +checklist: tuple
      +suggested_owner: str
      +blockers: tuple
      +next_action: str
    }
    class ApiEnablement {
      +systems: tuple
      +api_available: bool
      +api_required: bool
      +blocker: str
      +enabling_action: str
      +target_after_enablement: MigrationTarget
    }
    class AnalysisResult {
      +run_id: str
      +recommendations: list
      +clusters: list
      +component_candidates: list
      +api_matrix: list
      +sensitivity: dict
      +by_target(target) list
      +by_wave(wave) list
    }
    class SimilarityScorer {
      <<port>>
      +score(a: Taskbot, b: Taskbot) float
    }
    class TrainableSimilarityScorer {
      <<port>>
      +fit(bots: list) void
    }

    AnalysisResult "1" --> "*" Recommendation
    Recommendation --> ReviewPlan
    Recommendation --> EvidencePack
    Recommendation --> ApiEnablement
    TrainableSimilarityScorer --|> SimilarityScorer
```

`TrainableSimilarityScorer` existe para scorers que necesitan calibrarse con todo el portafolio.
`RapidFuzzSimilarity.fit(bots)` detecta aplicaciones hub para que SAP, Outlook o SharePoint no
inflen falsos positivos de similitud.

## Reglas de negocio

| Regla | Decision |
|---|---|
| Sin interaccion reconocida | revision manual profunda |
| UI legacy | RPA selectivo |
| Cluster grande sin legacy | microservice |
| Base de datos sin legacy | custom Python/Java |
| API, archivo o email | n8n |
| Alto riesgo + dependencias relevantes | gate de gobierno |
| Valor alto + complejidad baja + sin gate | Ola 1 |
| Valor medio/alto + complejidad controlada | Ola 2 |
| Resto | Ola 3 |

## Decisiones de arquitectura

Los ADRs completos estan en `docs/adr/`. Resumen:

1. **Hexagonal ligera**: suficiente separacion sin convertir una PoC en microservicios.
2. **Reglas deterministas**: mismas entradas producen mismas decisiones; el resultado es explicable.
3. **Similitud multi-senal**: evidencia declarada, apps no hub y texto; evita duplicados falsos por
   herramientas comunes.
4. **Agente opcional**: el LLM puede redactar mejor, pero no cambia decisiones y tiene fallback.
5. **n8n desacoplado**: n8n orquesta `POST /analyze`; puede reemplazarse por Appian, Power Platform
   o un BPM sin cambiar dominio.

## Seguridad y recuperacion

- Sin secretos en codigo.
- `TASKBOT_INVENTORY_ROOT` limita rutas aceptadas por `/analyze`.
- `/analyze/inline` evita exponer rutas locales.
- El servicio es stateless y de solo lectura sobre el inventario.
- Recuperacion ante fallo: corregir entrada/configuracion y volver a ejecutar.
- Cada corrida escribe en `reports/<run_id>/`.

## Validacion

La evidencia viva esta en `docs/evidencia_pruebas.txt`. La compuerta de CI ejecuta:

- tests,
- verificacion de OpenAPI,
- drift check del reporte ejemplo,
- `docker compose config`,
- smoke de n8n importando y ejecutando el workflow local.
