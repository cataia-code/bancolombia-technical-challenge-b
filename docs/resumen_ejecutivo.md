# Resumen ejecutivo

## Contexto

Un portafolio de RPA (taskbots) crece de forma fragmentada: automatizaciones duplicadas, atadas a
UI legacy y con criterios de migración dispersos. Decidir manualmente qué migrar, consolidar o
reemplazar es lento, subjetivo y difícil de defender ante arquitectura y operación.

## Solución

**Taskbot Migration Advisor**: un servicio local que recibe el inventario de taskbots y genera
**recomendaciones accionables y justificadas** de consolidación y migración. Combina **reglas
deterministas** (reproducibles) con **similitud multi-señal** para detectar duplicidad, y una
capa de **agente opcional** que enriquece las justificaciones sin alterar las decisiones.

## Qué entrega

Sobre el inventario real de 50 taskbots, en segundos y sin ambientes del cliente:

- **15 grupos consolidables** detectados (variantes de una misma utilidad).
- Clasificación de destino: **8 → n8n**, **5 → Python/Java a la medida**, **1 → microservicio
  compartido**, **36 → RPA selectivo** (portafolio fuertemente atado a SAP/UI legacy).
- Priorización en **olas** (Ola 1 = alto valor / baja complejidad = quick wins).
- Reducción de evaluación manual: **27 gates de gobierno** se separan en **19 asistidos por
  IA/aprobación dirigida** y **8 de evaluación manual profunda**.
- `EvidencePack` por taskbot: dependencias, controles, checklist, owner, bloqueadores y siguiente
  acción para que la revisión asistida sea auditable.
- Matriz API con `destino_objetivo_post_habilitacion`: muestra qué RPA selectivo puede pasar a n8n
  o Python/Java cuando se exponga integración.
- Sensibilidad de umbrales: compara complejidad 80/85/90 y dependencias 3/4 para calibrar la carga
  manual sin perder trazabilidad.
- **Justificación por decisión** ("por qué este taskbot va a este destino y a esta ola").
- Reporte **JSON** (máquina) + **HTML** (negocio) y **trazabilidad** estructurada por corrida.

## Hallazgo de negocio

El **72% del portafolio depende de UI legacy** (SAP GUI, mainframe, Citrix). La estrategia realista
no es forzar n8n, sino: (1) consolidar variantes, (2) exponer APIs donde hoy se navega UI para
**habilitar** migración futura, y (3) reservar RPA selectivo para lo que aún no tiene integración.

## Valor diferencial

- **Criterio, no ejecución mecánica**: el sistema *explica* cada recomendación.
- **Reproducible y auditable**: mismas entradas → mismas decisiones; todo trazable por `run_id`.
- **Bajo acoplamiento**: el orquestador (n8n) es reemplazable por Appian/Power Platform/BPM sin
  tocar la lógica de negocio; la fuente de inventario y la salida son intercambiables.
- **Sin sobreingeniería**: monolito modular hexagonal, un solo despliegue, dependencias mínimas.

## Cómo se demuestra

`docker compose up` levanta n8n + el servicio; el workflow dispara el análisis y muestra los
hallazgos. Alternativamente, un comando CLI produce los reportes localmente. La suite automatizada
en CI respalda la solución.
