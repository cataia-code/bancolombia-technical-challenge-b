"""Tests de integracion de la API HTTP que orquesta n8n."""

from pathlib import Path

from fastapi.testclient import TestClient

from taskbot_advisor.interface.api import app

client = TestClient(app)
TXT = (Path(__file__).resolve().parents[2] / "data" / "ejemplo_50_taskbots_prueba.txt").as_posix()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_ok():
    resp = client.post("/analyze", json={"inventory_path": TXT, "persist": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_taskbots"] == 50
    first = body["recommendations"][0]
    assert "evidence_pack" in first
    assert "destino_objetivo_post_habilitacion" in first["api_enablement"]
    assert "sensitivity" in body


def test_analyze_persist_escribe_reportes(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKBOT_REPORTS_DIR", str(tmp_path))
    resp = client.post("/analyze", json={"inventory_path": TXT, "run_id": "api_p", "persist": True})
    assert resp.status_code == 200
    assert (tmp_path / "api_p" / "reporte.json").exists()


def test_analyze_archivo_inexistente_da_400():
    resp = client.post("/analyze", json={"inventory_path": "no/existe.csv", "persist": False})
    assert resp.status_code == 400


def test_analyze_run_id_invalido_da_400():
    resp = client.post("/analyze", json={"inventory_path": TXT, "run_id": "../evil"})
    assert resp.status_code == 400


def test_analyze_inventory_root_bloquea_ruta_externa(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKBOT_INVENTORY_ROOT", str(tmp_path))
    resp = client.post("/analyze", json={"inventory_path": "../../etc/passwd", "persist": False})
    assert resp.status_code == 400


def test_analyze_inventory_root_permite_ruta_interna(tmp_path, monkeypatch):
    # Copia el inventario dentro del root permitido y verifica que sí carga.
    import shutil
    inv = tmp_path / "inv.txt"
    shutil.copy(TXT, inv)
    monkeypatch.setenv("TASKBOT_INVENTORY_ROOT", str(tmp_path))
    resp = client.post("/analyze", json={"inventory_path": "inv.txt", "persist": False})
    assert resp.status_code == 200
    assert resp.json()["summary"]["total_taskbots"] == 50


def test_inline_run_id_invalido_da_400():
    resp = client.post("/analyze/inline", json={"taskbots": [], "run_id": "bad id"})
    assert resp.status_code == 400


def test_analyze_inline():
    payload = {"taskbots": [
        {"nombre": "Bot API", "tipo_interaccion": "api", "frecuencia": "diaria", "riesgo": "bajo"},
        {"nombre": "Bot Legacy", "tipo_interaccion": "UI legacy", "frecuencia": "diaria", "riesgo": "alto"},
    ]}
    resp = client.post("/analyze/inline", json=payload)
    assert resp.status_code == 200
    destinos = resp.json()["summary"]["por_destino"]
    assert destinos["n8n"] == 1
    assert destinos["rpa_selective"] == 1


def test_openapi_usa_modelos_de_respuesta():
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    analysis = schemas["AnalysisResponse"]["properties"]
    assert analysis["summary"]["$ref"].endswith("/SummaryResponse")
    assert analysis["api_matrix"]["items"]["$ref"].endswith("/ApiMatrixResponse")
    assert schemas["RecommendationResponse"]["properties"]["score_breakdown"]["$ref"].endswith(
        "/ScoreBreakdownResponse"
    )
    assert schemas["RecommendationResponse"]["properties"]["evidence_pack"]["$ref"].endswith(
        "/EvidencePackResponse"
    )
