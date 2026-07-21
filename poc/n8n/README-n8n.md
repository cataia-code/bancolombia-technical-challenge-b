# Orquestacion con n8n

n8n actua como **orquestador**: dispara el analisis, invoca el servicio Python por HTTP,
recibe el JSON de recomendaciones y extrae los hallazgos accionables. La logica de negocio
(clasificacion, scoring, clustering y politica de revision) vive en el servicio, no en n8n.

## Flujo (`workflow.json`)

```
[Inicio manual] -> [Analizar inventario (HTTP POST /analyze)] -> [Extraer hallazgos (Code)]
```

- **Inicio manual**: dispara la ejecucion en la demo.
- **Analizar inventario**: `POST http://advisor:8000/analyze` y body
  `{"inventory_path": "ejemplo_50_taskbots_prueba.txt", "persist": true}`.
  El servicio corre con `TASKBOT_INVENTORY_ROOT=/app/data`, por lo que la ruta se resuelve
  dentro del volumen de inventarios montado en Docker. Tiene reintentos (3 intentos, 2s).
- **Extraer hallazgos**: transforma el resultado en frases de negocio y devuelve `run_id`,
  `headlines`, `resumen`, `revision`, `destinos_objetivo_post_habilitacion`, `sensibilidad`
  y el desglose `ola_3` (`complejidad_extrema`, `menor_valor`, `gate_gobierno`,
  `evaluacion_manual_profunda`, `asistida_ia`).

## Como importarlo

El stack usa `n8nio/n8n:2.30.5` pinneado para evitar cambios no reproducibles del tag `latest`.
En otro orquestador se conserva el contrato HTTP y se cambia la URL del nodo/cliente que invoque
`POST /analyze`.

1. Levanta el stack: `docker compose up --build`.
2. Abre n8n en http://localhost:5678.
3. Menu -> *Import from File* -> selecciona `n8n/workflow.json`.
4. Ejecuta el workflow (*Test workflow*).
5. Revisa el nodo final y el reporte generado en `./reports/<run_id>/`.

## Validacion Docker sin UI

Para una verificacion tecnica reproducible, con `advisor` levantado:

```bash
docker compose run --rm --no-deps --entrypoint /bin/sh n8n /home/node/.n8n-import/smoke.sh
```

La ejecucion debe terminar con `status: success`; el ultimo nodo devuelve 50 taskbots y el desglose
de olas 7/29/14. La revision queda separada en 27 gates de gobierno: 19 asistidos por IA/aprobacion
dirigida y 8 de evaluacion manual profunda.

La misma validacion queda automatizada en CI: levanta `advisor` + `n8n`, valida `GET /health` y
`GET /healthz`, importa el workflow local y ejecuta `n8n execute` por el ID exportado.

## Mapeo a plataformas del cliente

Si en el cliente el orquestador es **Appian / Power Platform / un BPM**, el mismo contrato HTTP
aplica: el orquestador llama `POST /analyze` y consume el JSON. El servicio de analisis es
independiente del orquestador (bajo acoplamiento), por lo que migrar de n8n a otro orquestador
no toca la logica de negocio.
