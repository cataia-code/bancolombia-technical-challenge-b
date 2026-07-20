# Orquestación con n8n

n8n actúa como **orquestador**: dispara el análisis, invoca el servicio Python por HTTP,
recibe el JSON de recomendaciones y extrae los hallazgos accionables. La lógica de negocio
(clasificación, scoring, clustering) vive en el servicio, no en n8n — n8n orquesta, no decide.

## Flujo (`workflow.json`)

```
[Inicio manual] → [Analizar inventario (HTTP POST /analyze)] → [Extraer hallazgos (Code)]
```

- **Inicio manual**: dispara la ejecución en la demo.
- **Analizar inventario**: `POST http://advisor:8000/analyze` con
  `{"inventory_path": "/app/data/ejemplo_50_taskbots_prueba.txt", "persist": true}`.
  Tiene **reintentos** (3 intentos, 2s) — parte de la estrategia de recuperación ante fallo.
- **Extraer hallazgos**: nodo Code que transforma el resultado en las frases de negocio
  ("N taskbots son variantes de M utilidades", "K candidatos a n8n", etc.).

## Cómo importarlo

1. Levanta el stack: `docker compose up --build`.
2. Abre n8n en http://localhost:5678.
3. Menú → *Import from File* → selecciona `n8n/workflow.json`.
4. Ejecuta el workflow (*Test workflow*). El nodo final muestra los hallazgos y el `run_id`.
   El reporte HTML/JSON queda en `./reports/<run_id>/`.

## n8n Cloud (sin servicio local)

> ⚠️ **Solo fallback de demostración.** El nodo Code **duplica las reglas en JavaScript** únicamente
> porque n8n Cloud no puede alcanzar `localhost`. La **fuente única de verdad es el servicio Python**
> (`src/taskbot_advisor`): el port JS existe para poder *probar en la nube sin infraestructura*, no
> para producción. En un entorno real, n8n Cloud llama al servicio por HTTP (ver el túnel más abajo),
> conservando el principio de lógica reutilizable y sin duplicar reglas.

n8n Cloud no puede alcanzar `localhost`. Para probar en la nube se entrega
**`workflow.cloud.json`**: un workflow **autocontenido** con dos nodos
(*Inicio manual* → *Code*). El nodo Code lleva **el inventario embebido** y un
**port fiel en JavaScript** de las reglas, el scoring y el clustering; produce el
mismo resultado que el servicio Python (verificado: 15 grupos consolidables,
n8n 8 · microservicio 1 · Python/Java 5 · RPA selectivo 36; olas 2/7/41).

Importar en n8n Cloud:
1. n8n Cloud → *Workflows* → *Import from File* → `n8n/workflow.cloud.json`.
2. *Test workflow*. El nodo Code devuelve `summary`, `headlines` y `recommendations`.

Alternativa (usando el servicio real desde la nube): exponer el servicio local con
un túnel público (`cloudflared tunnel --url http://localhost:8000` o `ngrok http 8000`)
y apuntar el nodo HTTP de `workflow.json` a la URL pública `/analyze`.

## Mapeo a plataformas del cliente

Si en el cliente el orquestador es **Appian / Power Platform / un BPM**, el mismo contrato HTTP
aplica: el orquestador llama `POST /analyze` y consume el JSON. El servicio de análisis es
independiente del orquestador (bajo acoplamiento), por lo que migrar de n8n a otro orquestador
no toca la lógica de negocio.
