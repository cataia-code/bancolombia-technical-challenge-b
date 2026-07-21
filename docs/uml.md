# Diagramas UML

## Casos de uso

```mermaid
flowchart LR
    arq([Arquitecto de automatizacion])
    ops([Operacion])
    n8n([n8n / Orquestador])
    subgraph Sistema[Taskbot Migration Advisor]
      uc1((Analizar inventario))
      uc2((Detectar duplicidad))
      uc3((Clasificar destino))
      uc4((Priorizar en olas))
      uc5((Generar reporte))
      uc6((Definir gate de revision))
    end
    arq --> uc1
    ops --> uc5
    n8n --> uc1
    uc1 -.incluye.-> uc2
    uc1 -.incluye.-> uc3
    uc1 -.incluye.-> uc4
    uc1 -.incluye.-> uc5
    uc1 -.incluye.-> uc6
```

## Clases (dominio + aplicación + puertos)

```mermaid
classDiagram
    class Taskbot {
      +id: str
      +name: str
      +purpose: str
      +apps: tuple
      +interactions: tuple~InteractionType~
      +frequency: str
      +risk: RiskLevel
      +dependencies: tuple
      +known_similarity: str
      +normalized_text() str
      +has(interaction) bool
      +known_interactions: tuple
    }
    class InteractionType {
      <<enum>>
      +parse(raw) InteractionType
      +parse_many(raw) tuple
    }
    class RiskLevel {
      <<enum>>
      +parse(raw) RiskLevel
    }
    class MigrationTarget {
      <<enum>>
      +N8N
      +MICROSERVICE
      +CUSTOM_PYTHON_JAVA
      +RPA_SELECTIVE
      +MANUAL_REVIEW
    }
    class Wave {
      <<enum>>
      +WAVE_1
      +WAVE_2
      +WAVE_3
    }
    class ReviewStrategy {
      <<enum>>
      +NONE
      +AI_PRECHECK
      +TARGETED_APPROVAL
      +MANUAL_DEEP_DIVE
    }
    class Cluster {
      +id: int
      +member_ids: tuple
      +representative_id: str
      +size: int
      +is_duplicate_group: bool
    }
    class Recommendation {
      +taskbot_id: str
      +taskbot_name: str
      +decision: MigrationDecision
      +scores: ScoreExplanation
      +rationale: str
      +api_enablement: ApiEnablement
      +evidence_pack: EvidencePack
      +target: MigrationTarget
      +wave: Wave
      +value_score: float
      +complexity_score: float
      +review_strategy: ReviewStrategy
      +requires_governance_gate: bool
      +ai_assisted_review: bool
      +needs_manual_review: bool
      +score_breakdown: dict
    }
    class MigrationDecision {
      +target: MigrationTarget
      +wave: Wave
      +cluster_id: int
      +reasons: tuple
      +review: ReviewPlan
      +needs_manual_review: bool
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
    class ScoreExplanation {
      +value: float
      +complexity: float
      +breakdown: dict
    }
    class ApiEnablement {
      +systems: tuple
      +api_available: bool
      +api_required: bool
      +blocker: str
      +enabling_action: str
      +target_after_enablement: MigrationTarget
    }
    class ComponentCandidate {
      +cluster_id: int
      +suggested_name: str
      +member_ids: tuple
      +member_names: tuple
      +common_purpose: str
      +target_pattern: MigrationTarget
      +dominant_apps: tuple
      +legacy_blocker: bool
      +needs_api_enablement: bool
      +recommended_action: str
      +size: int
    }
    class AnalysisResult {
      +run_id: str
      +recommendations: list
      +clusters: list
      +errors: list
      +component_candidates: list
      +api_matrix: list
      +sensitivity: dict
      +total: int
      +by_target(target) list
      +by_wave(wave) list
      +consolidation_groups: list
    }
    class AnalyzeInventory {
      +execute(run_id: str) AnalysisResult
    }
    class InventoryRepository {
      <<port>>
      +load() tuple
    }
    class SimilarityScorer {
      <<port>>
      +score(a: Taskbot, b: Taskbot) float
    }
    class TrainableSimilarityScorer {
      <<port>>
      +fit(bots: list) void
    }
    class AgentAdvisor {
      <<port>>
      +explain(bot: Taskbot, rec: Recommendation) str
    }
    class ReportRenderer {
      <<port>>
      +render(result: AnalysisResult) str
    }
    class RunLoggerFactory {
      <<port>>
      +for_run(run_id: str) RunLogger
    }
    class RunLogger {
      <<port>>
      +info(event: str, fields) void
      +error(event: str, fields) void
    }

    AnalyzeInventory --> InventoryRepository
    AnalyzeInventory --> SimilarityScorer
    AnalyzeInventory --> RunLoggerFactory
    AnalyzeInventory --> AgentAdvisor
    AnalyzeInventory --> AnalysisResult
    AnalysisResult "1" --> "*" Recommendation
    AnalysisResult "1" --> "*" Cluster
    AnalysisResult "1" --> "*" ComponentCandidate
    Recommendation --> MigrationDecision
    Recommendation --> ScoreExplanation
    Recommendation --> ApiEnablement
    MigrationDecision --> ReviewPlan
    ReviewPlan --> ReviewStrategy
    ReviewPlan --> EvidencePack
    ApiEnablement --> MigrationTarget
    Taskbot --> InteractionType
    Taskbot --> RiskLevel
    MigrationDecision --> MigrationTarget
    MigrationDecision --> Wave
    ComponentCandidate --> MigrationTarget
    TrainableSimilarityScorer --|> SimilarityScorer
    RunLoggerFactory --> RunLogger
```

`TrainableSimilarityScorer` existe para scorers que necesitan calibrarse con todo el portafolio
antes de comparar pares. En esta implementación `RapidFuzzSimilarity.fit(bots)` detecta aplicaciones
"hub" para que SAP/Outlook/SharePoint no inflen falsos positivos de similitud.

## Secuencia (flujo principal)

```mermaid
sequenceDiagram
    participant U as CLI / n8n
    participant UC as AnalyzeInventory
    participant R as InventoryRepository
    participant S as SimilarityScorer
    participant D as Dominio (rules/review/scoring/api)
    participant A as AgentAdvisor
    participant W as Renderers

    U->>UC: execute(run_id)
    UC->>R: load()
    R-->>UC: taskbots, errores
    opt scorer entrenable
        UC->>S: fit(taskbots)  %% calibra apps hub por puerto explicito
    end
    UC->>D: build_clusters(taskbots, score, umbral)
    D-->>UC: clusters
    loop por taskbot
        UC->>D: classify_target + assess_review + scoring + api_enablement + wave
        D-->>UC: recommendation
        UC->>A: explain(bot, rec)
        A-->>UC: justificacion
    end
    UC->>D: build_component_candidates + system_matrix + build_review_sensitivity
    D-->>UC: catalogo, matriz API, sensibilidad
    UC-->>U: AnalysisResult
    U->>W: render(result) -> JSON + HTML
```

## Componentes

```mermaid
flowchart TB
    subgraph Interfaz
      CLI[CLI Typer]
      API[FastAPI]
    end
    subgraph Aplicacion
      UC[AnalyzeInventory]
      P[Puertos]
    end
    subgraph Dominio
      RULES[rules]
      REVIEW[review]
      SCORE[scoring]
      SIMD[similarity/clustering]
      ENT[entities]
    end
    subgraph Infraestructura
      REPO[Repos csv/json/sqlite/txt]
      SIM[RapidFuzzSimilarity]
      ADV[Advisor LLM/determinista]
      REND[Renderers JSON/HTML]
      CFG[config]
      LOG[logging JSON]
    end
    CLI --> UC
    API --> UC
    UC --> P
    UC --> RULES & REVIEW & SCORE & SIMD
    P -. implementan .- REPO & SIM & ADV & REND & LOG
    n8n[(n8n)] --> API
```

## Actividad (lógica de negocio)

```mermaid
flowchart TD
    A[Cargar inventario] --> B{Registro valido?}
    B -- no --> E[Registrar error, continuar]
    B -- si --> C[Normalizar]
    C --> D[Calibrar apps hub + clustering]
    D --> F{Interaccion reconocida?}
    F -- no --> G[Revision manual profunda]
    F -- si --> H{UI legacy?}
    H -- si --> I[RPA selectivo]
    H -- no --> J{Cluster grande?}
    J -- si --> K[Microservicio]
    J -- no --> L{BD?}
    L -- si --> M[Python/Java]
    L -- no --> N[n8n]
    G & I & K & M & N --> O[Assess review: sin gate / IA / aprobacion / manual profunda]
    O --> V[Evidence pack + destino post habilitacion API]
    V --> S[Scoring valor/complejidad -> ola]
    S --> Q{Ola 3?}
    Q -- si --> R[Etiquetar causa: complejidad extrema / menor valor / tipo revision]
    Q -- no --> T[Calcular sensibilidad de umbrales]
    R --> T
    T --> P[Justificar y reportar]
```
