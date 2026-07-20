# Runbook de demo y recuperación ante fallo

Guía corta para la socialización: cómo correr la demo, qué puede fallar y cómo recuperarse,
y qué evidencia mostrar en cada caso. No pretende ser un modelo operativo completo — es lo
mínimo para una demo local reproducible y defendible.

## Demo en un comando

```bash
# desde la raíz del repo
bash scripts/demo.sh          # Linux/macOS/Git-Bash
.\scripts\demo.ps1            # Windows PowerShell
```

Salida esperada: 50 taskbots, 15 grupos consolidables, 15 componentes catalogados, 0 errores,
y la ruta del reporte (`poc/reports/demo/reporte.html`).

## Fallos comunes y recuperación

| Síntoma | Causa probable | Recuperación | Evidencia a mostrar |
|---|---|---|---|
| `InventoryLoadError: ... does not exist` | Ruta de inventario incorrecta | Verificar la ruta; usar `poc/data/ejemplo_50_taskbots_prueba.txt` | El error es claro y no rompe el proceso |
| `ValueError: TASKBOT_SIMILARITY_THRESHOLD ...` | Config inválida (fail-fast) | Corregir la variable de entorno (0–100) | El servicio no arranca con config inválida (a propósito) |
| Un taskbot aparece en `errors` del reporte | Registro inválido en el inventario | El lote continúa (fail-soft); reprocesar solo ese registro | Campo `errors[]` en el JSON con `taskbot_id` y motivo |
| n8n Cloud no conecta al servicio | n8n Cloud no alcanza `localhost` | Usar `workflow.cloud.json` (autocontenido) o un túnel público al servicio | El workflow cloud corre sin servicio local |
| `docker compose up` falla | Docker no está corriendo / puertos ocupados | Iniciar Docker; liberar 8000/5678; o usar el CLI sin Docker | El CLI produce el mismo reporte sin infraestructura |
| Reportes previos "desaparecen" | — (no ocurre) | Cada corrida escribe en `reports/<run_id>/` sin sobrescribir | Carpetas por `run_id`, idempotentes |
| `HTTP 400` en `/analyze` | `run_id` inválido o ruta fuera de `TASKBOT_INVENTORY_ROOT` | Usar `run_id` `[A-Za-z0-9_-]`; ruta relativa dentro del root | Guardrails de seguridad activos |

## Rollback / recuperación (resumen)

El servicio es *stateless* y de solo lectura sobre el inventario: **no hay estado que revertir**.
Recuperarse ante un fallo = **volver a ejecutar**. Las corridas son idempotentes y versionadas por
`run_id`; el nodo HTTP de n8n reintenta 3 veces; un ítem fallido queda aislado en `errors` y puede
reprocesarse sin repetir todo el lote.

## Checklist previo a la demo

- [ ] `python -m pytest` en `poc/` → 111 passed, 100% cobertura.
- [ ] `bash scripts/demo.sh` → imprime hallazgos y valida el resumen.
- [ ] Abrir `poc/reports/demo/reporte.html` (catálogo de componentes + matriz API).
- [ ] (Opcional) `docker compose up --build` y disparar el workflow en n8n (`:5678`).
