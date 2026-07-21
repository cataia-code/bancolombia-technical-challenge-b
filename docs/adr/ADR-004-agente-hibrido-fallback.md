# ADR-004: Agente hibrido con fallback determinista

## Estado
Aceptado

## Contexto
El reto pide "criterio asistido por agente" pero tambien correr **localmente, sin credenciales ni
servicios externos obligatorios**, y de forma **reproducible**. Un LLM aporta justificaciones mas
naturales y puede preparar evidencia/checklists para revision, pero no puede ser una dependencia
critica ni decidir por el sistema.

## Decision
Definir el puerto `AgentAdvisor` con dos implementaciones: `DeterministicAdvisor` (por defecto,
compone la justificacion a partir de razones, puntajes y `ReviewPlan`) y `LlmAdvisor` (opcional).
El LLM **solo explica una decision ya tomada** y puede redactar mejor la accion de revision; nunca
cambia el destino, la ola ni la politica de revision.

Se activa solo si `TASKBOT_LLM_ENABLED=true` **y** hay `ANTHROPIC_API_KEY`; ante cualquier fallo
(red, cuota, libreria ausente) degrada al determinista. La salida determinista ya propone la
intervencion de IA en `accion_revision` para reducir trabajo manual sin depender de servicios
externos en la demo.

## Consecuencias
- (+) La demo corre offline y reproducible; el LLM es un "plus" opcional.
- (+) Las decisiones nunca dependen del LLM: auditable y estable.
- (+) La politica de revision reduce cola manual: IA prepara evidencia y checklist, humanos revisan
  solo casos extremos o aprobaciones puntuales.
- (-) La justificacion por defecto es mas mecanica que la del LLM; el contenido de la decision es
  identico.

## Alternativas consideradas
- **Sin LLM**: cede el punto de "criterio asistido por agente" que el reto valora.
- **LLM obligatorio / como nucleo**: viola la restriccion de reproducibilidad y de no depender de
  servicios externos.
