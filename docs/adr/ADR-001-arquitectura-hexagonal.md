# ADR-001: Arquitectura hexagonal ligera en un monolito modular

## Estado
Aceptado

## Contexto
El reto exige demostrar criterio de diseño con una solución local, mantenible y defendible, sin
sobreingeniería. El valor real está en el criterio de negocio (clasificación, scoring, clustering),
que debe ser estable, explicable y testeable; mientras que las fuentes de inventario, la salida y el
orquestador deben poder cambiar (n8n hoy, Appian/Power Platform mañana).

## Decisión
Adoptar **arquitectura hexagonal (ports & adapters)** dentro de un **monolito modular**: un núcleo de
dominio puro (sin I/O), un caso de uso que orquesta dependiendo de puertos, y adapters de
infraestructura que los implementan. Un solo despliegue.

## Consecuencias
- (+) Dominio testeable sin mocks pesados; reglas aisladas de frameworks.
- (+) Cambiar fuente (CSV↔SQLite↔TXT), salida (JSON↔HTML) u orquestador no toca el núcleo.
- (+) Onboarding claro: cada capa tiene una responsabilidad.
- (−) Más archivos/indirección que un script único (asumido: el reto pide diseño evolutivo).

## Alternativas consideradas
- **Script único (como el discovery de la Parte A)**: excelente para un POC, pero no evidencia el
  criterio de arquitectura evolutiva que pide la Parte B.
- **Microservicios**: innecesario (un solo dominio); fragmentaría sin beneficio.
- **Capas clásicas**: acoplan dominio a persistencia; hexagonal invierte esa dependencia.
