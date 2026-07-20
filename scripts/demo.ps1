<#
One-command demo (Windows PowerShell): runs the analysis, prints the actionable
headlines and the report path. Intended for the socialization/demo session.

Usage (from repo root):  .\scripts\demo.ps1
#>
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "poc")

$py = "python"
if (Test-Path ".venv\Scripts\python.exe") { $py = ".venv\Scripts\python.exe" }

$inv = "data\ejemplo_50_taskbots_prueba.txt"
$runId = "demo"

Write-Host "== Taskbot Migration Advisor - demo =="
Write-Host "Inventario: $inv`n"

$env:PYTHONPATH = "src"
& $py -m taskbot_advisor analyze $inv --run-id $runId --quiet

$report = "reports\$runId\reporte.json"
Write-Host "Reporte JSON: poc\$report"
Write-Host "Reporte HTML: poc\reports\$runId\reporte.html`n"
Write-Host "== Hallazgos accionables =="

& $py - $report @'
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
assert s["total_taskbots"] == 50, "se esperaban 50 taskbots"
assert s["errores"] == 0, "hubo errores en el analisis"
print("\nOK: resumen validado (50 taskbots, 0 errores).")
'@
