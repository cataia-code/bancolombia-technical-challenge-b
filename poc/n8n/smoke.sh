#!/bin/sh
set -eu

WORKFLOW_ID="b1a1e001-0000-4001-8001-000000000000"
WORKFLOW_PATH="/home/node/.n8n-import/workflow.json"
OUTPUT_PATH="/tmp/n8n-output.json"

echo "Importing local workflow..."
n8n import:workflow --input="$WORKFLOW_PATH" >/tmp/import.log

echo "Executing workflow $WORKFLOW_ID..."
if ! n8n execute --id="$WORKFLOW_ID" --rawOutput >"$OUTPUT_PATH"; then
  cat "$OUTPUT_PATH"
  exit 1
fi

node - "$OUTPUT_PATH" <<'NODE'
const fs = require("fs");

const outputPath = process.argv[2];
const raw = fs.readFileSync(outputPath, "utf8");
const checks = [
  ['"status": "success"', "workflow status"],
  ['"total_taskbots": 50', "taskbot count"],
  ['"ola_1": 7', "wave 1 count"],
  ['"ola_2": 29', "wave 2 count"],
  ['"ola_3": 14', "wave 3 count"],
  ['"asistida_ia": 19', "AI-assisted review count"],
  ['"manual_profunda": 8', "deep manual review count"],
  ['"destinos_objetivo_post_habilitacion"', "post-API target summary"],
  ['"sensibilidad"', "threshold sensitivity summary"],
];

for (const [pattern, label] of checks) {
  if (!raw.includes(pattern)) {
    console.error(`Missing ${label}: ${pattern}`);
    process.exit(1);
  }
}

console.log("n8n smoke ok: 50 taskbots, waves 7/29/14, review 19 assisted / 8 manual, sensitivity and post-API targets present.");
NODE
