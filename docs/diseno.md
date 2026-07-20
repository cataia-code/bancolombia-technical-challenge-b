# Documento de diseño

## 1. Entendimiento del reto

Construir una solución **local y reproducible** que reciba un inventario de taskbots (RPA) y genere
**recomendaciones de consolidación y migración**. No es "hacer un bot": es demostrar **criterio de
diseño** para convertir una masa de automatizaciones fragmentadas en decisiones accionables.

**Entrada**: inventario con nombre, propósito, aplicaciones, tipo(s) de interacción, frecuencia,
riesgo, dependencias y evidencia de duplicidad.
**Salida**: por cada taskbot, un destino tecnológico sugerido, una ola de migración, puntajes de
valor/complejidad y una justificación; más grupos consolidables y un reporte JSON+HTML.
**Restricción clave**: sin ambientes, credenciales ni servicios externos obligatorios.

### Requisitos funcionales

| ID | Requisito | Criterio de aceptación |
|----|-----------|------------------------|
| RF1 | Cargar inventario local | Lee .txt/.csv/.json/.sqlite; registros inválidos no abortan el lote |
| RF2 | Normalizar atributos | Tipos de interacción, riesgo y frecuencia se canonizan (tolerante a sinónimos) |
| RF3 | Detectar duplicidad | Agrupa variantes en clusters; expone grupos consolidables |
| RF4 | Clasificar destino | Cada taskbot recibe uno de: n8n / microservicio / Python-Java / RPA selectivo / revisión manual |
| RF5 | Priorizar | Asigna Ola 1/2/3 por valor vs. complejidad |
| RF6 | Justificar | Cada recomendación incluye razones explícitas |
| RF7 | Reportar | Genera JSON + HTML con hallazgos accionables |
| RF8 | Trazar | Logs estructurados con `run_id`; errores registrados por ítem |

### Requisitos no funcionales

Reproducibilidad (mismas entradas → mismas decisiones), testabilidad (dominio puro), bajo
acoplamiento (puertos/adapters), extensibilidad (nuevos destinos/reglas/fuentes sin tocar el
núcleo), observabilidad (logs JSON + `run_id`), portabilidad (local, Docker), seguridad (sin
secretos embebidos; el LLM es opcional).

### Supuestos

| Supuesto | Justificación | Riesgo si es falso |
|----------|---------------|--------------------|
| El inventario declara evidencia de duplicidad textual | Es un campo del formato provisto | Baja detección de duplicados no declarados (mitigado con similitud de apps/texto) |
| El tipo de interacción refleja la vía de integración real | Base para clasificar destino | Clasificación imprecisa; se marca revisión manual ante ambigüedad |
| UI legacy es el factor bloqueante de migración | Criterio estándar de RPA | Sobre-asignación a RPA selectivo (aceptable y conservador) |

### Preguntas abiertas

- ¿Existe una tabla de "volumen mensual / criticidad" por bot? Permitiría afinar el valor (hoy se
  infiere de la frecuencia).
- ¿La organización tiene un catálogo de APIs existentes? Cambiaría "RPA selectivo" por "n8n" en los
  casos donde ya hay API disponible para el sistema legacy.

## 2. Arquitectura

**Elegida: hexagonal (ports & adapters) ligera dentro de un monolito modular.**

El núcleo de valor —reglas de clasificación, scoring y clustering— es **puro** (sin I/O) y por tanto
estable y trivialmente testeable. Las orillas —fuente de inventario, salida de reportes, agente LLM
y API HTTP— son **adapters** detrás de puertos (`InventoryRepository`, `SimilarityScorer`,
`AgentAdvisor`, `ReportRenderer`). El caso de uso `AnalyzeInventory` orquesta el flujo dependiendo
solo de abstracciones.

```
Interfaz (CLI / FastAPI)  →  Aplicación (AnalyzeInventory, ports)  →  Dominio (reglas, scoring, clustering)
                                        ↑ (adapters implementan los puertos)
Infraestructura: repos (csv/json/sqlite/txt), similitud rapidfuzz, advisor (LLM|determinista), renderers, config, logging
```

### Alternativas descartadas

- **Microservicios**: no aplica — un solo dominio, un solo despliegue. Fragmentaría sin beneficio.
- **Arquitectura por capas clásica**: acopla el dominio a la persistencia; dificulta test y cambio
  de fuente. Hexagonal da el mismo orden con inversión de dependencias.
- **Agente LLM como núcleo**: rompería la reproducibilidad y la restricción de correr sin
  credenciales. Se relega a capa opcional.

### Trade-offs aceptados

- Un pequeño acoplamiento pragmático: el caso de uso invoca un hook opcional `fit()` del scorer para
  calibrar apps "hub". Se resuelve por duck-typing (no obliga a todos los scorers a implementarlo).
- La similitud usa rapidfuzz (dependencia) en vez de solo stdlib: mejor calidad en nombres en
  español a cambio de una dependencia ligera.

## 3. Modelo de dominio

- **Taskbot** (value object): id, nombre, propósito, apps, `interactions` (conjunto), frecuencia,
  riesgo, dependencias, evidencia de duplicidad.
- **InteractionType / RiskLevel** (enums con `parse`/`parse_many` tolerantes a sinónimos).
- **Cluster**: grupo de variantes (union-find); `is_duplicate_group` si tiene ≥2 miembros.
- **Recommendation**: destino, ola, valor, complejidad, razones, `needs_manual_review`, justificación.
- **AnalysisResult**: recomendaciones + clusters + errores; consultas por destino/ola.

## 4. Reglas de negocio

| Regla | Descripción | Dónde | Cómo se prueba |
|-------|-------------|-------|----------------|
| Sin interacción reconocida → revisión manual | No se puede clasificar destino | `domain/rules.py` | `test_rules::test_tipo_desconocido...` |
| UI legacy presente → RPA selectivo | El eslabón frágil domina | `domain/rules.py` | `test_ui_legacy_domina...` |
| Cluster ≥3 (sin legacy) → microservicio | Utilidad reutilizable compartida | `domain/rules.py` | `test_cluster_grande_no_legacy...` |
| BD presente → Python/Java a la medida | Lógica de datos | `domain/rules.py` | `test_database_sin_legacy...` |
| API/email/archivo → n8n | Integración orquestable | `domain/rules.py` | `test_api_va_a_n8n` |
| Alto riesgo + ≥3 dependencias → flag revisión | Ortogonal al destino | `domain/rules.py` | `test_revision_manual_es_flag...` |
| Ola 1 = valor≥50 y complejidad≤40 | Quick wins | `domain/scoring.py` | `test_ola_1...` |

Detección de duplicidad: **union-find** sobre pares cuya similitud ≥ umbral. Similitud = máximo de
(evidencia declarada) y una mezcla ponderada de (solapamiento de apps no-hub) y (texto rapidfuzz).
Ver [ADR-003](adr/ADR-003-similitud-multisenal.md).

## 5. Manejo de errores

- **Validación / inventario** (`InvalidTaskbotError`): fail-soft por ítem → el registro va a `errors`,
  el lote continúa.
- **Carga de fuente** (`InventoryLoadError`): archivo ausente/ilegible → 400 en la API, mensaje claro.
- **Configuración** (`ValueError` en `Settings.from_env`): fail-fast (no se arranca con config inválida).
- **LLM**: cualquier fallo (red, cuota, credencial) → fallback determinista, sin interrumpir.
- **Inesperados por ítem**: capturados en el caso de uso, registrados con `exc_info` y `run_id`.

## 6. Seguridad

Sin secretos en código (credencial del LLM solo por variable de entorno). El servicio es de solo
lectura sobre el inventario. Entradas validadas (Pydantic en la API; parseo tolerante en el mapper).
Logs sin datos sensibles (solo ids/atributos de clasificación). El LLM es opcional y desactivado por
defecto, por lo que la demo no envía datos a terceros.

**Guardrails del endpoint (`infrastructure/security.py`)** para exposición externa:
`run_id` validado por regex `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (no escapa el directorio de reportes);
`inventory_path` contenido dentro de `TASKBOT_INVENTORY_ROOT` si se define (rechaza rutas absolutas y
`..`); y `/analyze/inline` como endpoint recomendado para exposición externa (el inventario viaja en
el cuerpo, sin ruta local).

## 6.b. Plan de racionalización (salida enriquecida)

La salida va más allá de "recomendación por taskbot" (alineado con la Parte A):
- **Catálogo de componentes reutilizables** (`domain/catalog.py`): por cada cluster consolidable, un
  `ComponentCandidate` con nombre sugerido, propósito común, patrón destino, apps dominantes, blocker
  legacy, `needs_api_enablement` y acción recomendada.
- **Matriz API/no-API** (`domain/api_enablement.py`): por sistema (agregada) y por operación
  (`api_available`, `api_required`, `blocker`, `enabling_action`).
- **Scoring explicable** (`domain/scoring.py::score_breakdown`): desglose por frecuencia, riesgo,
  duplicidad, complejidad por interacción y dependencias.

## 7. Observabilidad

Logs estructurados en JSON (`infrastructure/logging.py`) con `run_id` como correlation id en cada
línea: `inventario_cargado`, `clusters_detectados`, `analisis_completado`, `fallo_taskbot`. Métricas
derivables del resumen (conteos por destino/ola/errores). Reportes versionados por `run_id`.

## 8. Rollback / recuperación

El servicio no muta la fuente y es idempotente: reprocesar produce una carpeta `reports/<run_id>/`
nueva sin destruir corridas previas. No hay estado transaccional que revertir; "recuperarse" =
volver a ejecutar. El nodo HTTP de n8n reintenta (3×, 2s). Un ítem fallido queda aislado en `errors`
y puede reprocesarse sin repetir todo el lote.

## 9. Plan de pruebas

| ID | Escenario | Tipo | Prioridad |
|----|-----------|------|-----------|
| T1 | Cada tipo de interacción → destino esperado | unit | alta |
| T2 | UI legacy domina sobre API/BD | unit | alta |
| T3 | Scoring y asignación de ola (bordes) | unit | alta |
| T4 | Clustering union-find (duplicados/transitividad) | unit | alta |
| T5 | Parseo multivaluado de interacciones | unit | media |
| T6 | Carga real .txt (50 taskbots) | integración | alta |
| T7 | Pipeline e2e produce todas las categorías | integración | alta |
| T8 | Reproducibilidad (dos corridas idénticas) | integración | alta |
| T9 | Reportes versionados por run_id | integración | media |
| T10 | API /health, /analyze, /analyze/inline, error 400 | integración | alta |

Casos borde cubiertos: inventario vacío/registro inválido, campos faltantes, duplicados,
LLM caído (fallback), archivo inexistente. **111 pruebas, 100% de cobertura** (umbral `fail_under = 100`).
Evidencia: [`evidencia_pruebas.txt`](evidencia_pruebas.txt).

## 10. Mejoras futuras

- Incorporar volumen/criticidad reales para afinar el valor (hoy inferido de la frecuencia).
- Catálogo de APIs existentes para reclasificar legacy con API disponible.
- Embeddings semánticos como cuarta señal de similitud (con fallback a rapidfuzz).
- Persistir histórico de corridas para comparar evolución del portafolio entre olas.
