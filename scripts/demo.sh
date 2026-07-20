#!/usr/bin/env bash
# One-command demo: runs the analysis, prints the actionable headlines and the
# report path. Intended for the socialization/demo session.
#
# Usage (from repo root):  bash scripts/demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/poc"

PY="python"
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"; fi
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi

INV="data/ejemplo_50_taskbots_prueba.txt"
RUN_ID="demo"

echo "== Taskbot Migration Advisor · demo =="
echo "Inventario: $INV"
echo

PYTHONPATH=src "$PY" -m taskbot_advisor analyze "$INV" --run-id "$RUN_ID" --quiet

REPORT="reports/$RUN_ID/reporte.json"
echo "Reporte JSON: poc/$REPORT"
echo "Reporte HTML: poc/reports/$RUN_ID/reporte.html"
echo
echo "== Hallazgos accionables =="
PYTHONPATH=src "$PY" - "$REPORT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
s = d["summary"]
groups = [c for c in d["clusters"] if c["es_grupo_consolidable"]]
variantes = sum(len(c["miembros"]) for c in groups)
print(f"- {variantes} taskbots son variantes de {len(groups)} utilidades reutilizables.")
print(f"- {s['por_destino']['n8n']} candidatos a n8n (API/archivo/email).")
print(f"- {s['por_destino']['rpa_selective']} en RPA selectivo por UI legacy.")
print(f"- {s['por_destino']['microservice']} a microservicio/componente compartido.")
print(f"- {s['por_ola']['ola_1']} en ola 1 (alto valor, baja complejidad).")
print(f"- {len(d['component_candidates'])} componentes reutilizables catalogados.")
# Basic validation of expected shape.
assert s["total_taskbots"] == 50, "se esperaban 50 taskbots"
assert s["errores"] == 0, "hubo errores en el análisis"
print("\nOK: resumen validado (50 taskbots, 0 errores).")
PY
