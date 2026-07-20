# ADR-002: Clasificación de destino por reglas deterministas explicables

## Estado
Aceptado

## Contexto
El sistema debe decidir a qué destino migra cada taskbot (n8n, microservicio, Python/Java, RPA
selectivo, revisión manual) y **explicar por qué**. El reto valora "claridad para explicar por qué el
sistema recomienda cada decisión" y "combinar reglas determinísticas con criterio asistido por agente".

## Decisión
Modelar la clasificación como un **conjunto ordenado de reglas deterministas** sobre atributos
observables (tipos de interacción, riesgo, dependencias, pertenencia a cluster). La primera regla que
aplica gana; cada regla emite una **razón textual**. La presencia de **UI legacy domina** (eslabón
frágil → RPA selectivo). `needs_manual_review` es una **bandera ortogonal** al destino.

## Consecuencias
- (+) Decisiones reproducibles y auditables; cada una trae su justificación.
- (+) Fácil de extender (nueva regla) y de probar (una prueba por regla).
- (−) No captura matices no codificados; se mitiga con la capa de agente (ADR-004) y la bandera de
  revisión manual.

## Alternativas consideradas
- **Clasificador ML**: sin datos etiquetados ni reproducibilidad garantizada; opaco para la demo.
- **LLM decide el destino**: rompe reproducibilidad y la restricción de correr sin credenciales.
