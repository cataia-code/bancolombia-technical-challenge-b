# ADR-005: n8n como orquestador desacoplado vía contrato HTTP

## Estado
Aceptado

## Contexto
El reto valora "buen uso de n8n como orquestador" y exige "un flujo de n8n exportable o documentado",
pero también que la demostración **corra localmente** y que la propuesta pueda **mapearse** a Appian /
Power Platform / BPM sin depender de ellos.

## Decisión
Exponer la lógica de análisis como un **servicio HTTP (FastAPI)** con un contrato simple
(`POST /analyze`). n8n orquesta llamando a ese endpoint; la lógica de negocio **no vive en n8n**. Se
entrega `n8n/workflow.json` importable y un `docker-compose` que levanta n8n + el servicio. El nodo
HTTP incluye reintentos.

## Consecuencias
- (+) Bajo acoplamiento: cambiar de n8n a otro orquestador es cambiar quién llama al endpoint.
- (+) La misma solución se demuestra por CLI (sin n8n) o por n8n (orquestada).
- (+) Reintentos en el orquestador = primera línea de recuperación ante fallo.
- (−) Introduce un servicio HTTP y Docker en la demo (asumido: es la forma esperada y aporta realismo).

## Alternativas consideradas
- **Toda la lógica en nodos de n8n**: acopla el criterio de negocio al orquestador, dificulta pruebas
  y portabilidad; contradice el mapeo a otras plataformas.
- **Solo CLI**: no evidencia el uso de n8n como orquestador que el reto pide.
