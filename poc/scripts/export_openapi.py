"""Export the FastAPI OpenAPI schema to a versioned file (contracts/openapi.json).

Keeping the contract in the repo (and validating it in CI, see deploy.yml) makes
the integration surface explicit and reinforces low coupling: any orchestrator
(n8n, Appian, Power Platform) codes against this contract.

Usage (from poc/):  python scripts/export_openapi.py
CI uses --check to fail if the committed file is stale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make 'src' importable when run directly (mirrors pyproject pythonpath).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from taskbot_advisor.interface.api import app  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    content = render()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            print("openapi.json esta desactualizado. Ejecuta: python scripts/export_openapi.py")
            return 1
        print("openapi.json actualizado.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"Escrito {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
