# ADR-002: Clasificacion de destino por reglas deterministas explicables

## Estado
Aceptado

## Contexto
El sistema debe decidir a que destino migra cada taskbot (n8n, microservicio, Python/Java,
RPA selectivo o revision manual cuando no se puede clasificar) y **explicar por que**. El reto
valora claridad, reproducibilidad y criterio asistido por agente, pero no conviene que todo caso
de alto riesgo termine en una cola manual amplia.

## Decision
Modelar la clasificacion de destino como un **conjunto ordenado de reglas deterministas** sobre
atributos observables (tipos de interaccion, pertenencia a cluster y presencia de UI legacy). La
primera regla que aplica gana; cada regla emite una razon textual. La presencia de **UI legacy
domina** (eslabon fragil -> RPA selectivo).

La revision se separa en `domain/review.py` mediante `ReviewPlan`: sin revision, prechequeo IA,
aprobacion dirigida o evaluacion manual profunda. Esto mantiene el gate de gobierno sin convertir
automaticamente cada alto riesgo en una revision manual completa.

## Consecuencias
- (+) Decisiones reproducibles y auditables; cada una trae su justificacion.
- (+) Facil de extender: nuevas reglas de destino y nuevas politicas de revision evolucionan por
  separado.
- (+) Reduce trabajo manual: la IA prepara evidencia/checklists y solo los casos extremos quedan
  como evaluacion manual profunda.
- (-) No captura matices no codificados; se mitiga con la capa de agente (ADR-004) y con razones
  explicables por recomendacion.

## Alternativas consideradas
- **Clasificador ML**: sin datos etiquetados ni reproducibilidad garantizada; opaco para la demo.
- **LLM decide el destino**: rompe reproducibilidad y la restriccion de correr sin credenciales.
