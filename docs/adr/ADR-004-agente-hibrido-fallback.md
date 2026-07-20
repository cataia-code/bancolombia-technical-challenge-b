# ADR-004: Agente híbrido con fallback determinista

## Estado
Aceptado

## Contexto
El reto pide "criterio asistido por agente" pero también correr **localmente, sin credenciales ni
servicios externos obligatorios**, y de forma **reproducible**. Un LLM aporta justificaciones más
naturales, pero no puede ser una dependencia crítica.

## Decisión
Definir el puerto `AgentAdvisor` con dos implementaciones: `DeterministicAdvisor` (por defecto,
compone la justificación a partir de razones y puntajes) y `LlmAdvisor` (opcional). El LLM **solo
redacta la justificación de una decisión ya tomada**; nunca cambia el destino ni la ola. Se activa
solo si `TASKBOT_LLM_ENABLED=true` **y** hay `ANTHROPIC_API_KEY`; ante cualquier fallo (red, cuota,
librería ausente) degrada al determinista.

## Consecuencias
- (+) La demo corre 100% offline y reproducible; el LLM es un "plus" opcional.
- (+) Las decisiones nunca dependen del LLM → auditable y estable.
- (−) La justificación por defecto es más mecánica que la del LLM (aceptable; el contenido de la
  decisión es idéntico).

## Alternativas consideradas
- **Sin LLM**: cede el punto de "criterio asistido por agente" que el reto valora.
- **LLM obligatorio / como núcleo**: viola la restricción de reproducibilidad y de no depender de
  servicios externos.
