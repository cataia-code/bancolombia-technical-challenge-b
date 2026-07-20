"""Tests de los repositorios de inventario (formatos y rutas de error)."""

import json
import sqlite3

import pytest

from taskbot_advisor.domain.exceptions import InventoryLoadError
from taskbot_advisor.infrastructure.repositories.file_repositories import (
    CsvInventoryRepository,
    JsonInventoryRepository,
    SqliteInventoryRepository,
    TxtInventoryRepository,
    repository_for,
)

ROW = {"nombre": "Bot API", "tipo_interaccion": "api", "frecuencia": "diaria", "riesgo": "bajo"}


def test_csv_load_y_fail_soft(tmp_path):
    p = tmp_path / "inv.csv"
    p.write_text("nombre,tipo_interaccion,frecuencia,riesgo\nBot A,api,diaria,bajo\n,,,\n",
                 encoding="utf-8")
    bots, errors = CsvInventoryRepository(p).load()
    assert len(bots) == 1          # la fila sin nombre no aborta el lote
    assert len(errors) == 1


def test_csv_archivo_inexistente(tmp_path):
    with pytest.raises(InventoryLoadError):
        CsvInventoryRepository(tmp_path / "no.csv").load()


def test_json_lista(tmp_path):
    p = tmp_path / "inv.json"
    p.write_text(json.dumps([ROW]), encoding="utf-8")
    bots, errors = JsonInventoryRepository(p).load()
    assert len(bots) == 1 and errors == []


def test_json_con_clave_taskbots(tmp_path):
    p = tmp_path / "inv.json"
    p.write_text(json.dumps({"taskbots": [ROW]}), encoding="utf-8")
    bots, _ = JsonInventoryRepository(p).load()
    assert bots[0].name == "Bot API"


def test_json_archivo_inexistente(tmp_path):
    with pytest.raises(InventoryLoadError):
        JsonInventoryRepository(tmp_path / "no.json").load()


def test_json_invalido(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{no es json", encoding="utf-8")
    with pytest.raises(InventoryLoadError):
        JsonInventoryRepository(p).load()


def test_json_estructura_no_soportada(tmp_path):
    p = tmp_path / "n.json"
    p.write_text(json.dumps({"otra": 1}), encoding="utf-8")
    # dict sin 'taskbots' -> lista vacia -> carga vacia (no error de estructura)
    bots, _ = JsonInventoryRepository(p).load()
    assert bots == []


def test_json_numero_top_level_es_error(tmp_path):
    p = tmp_path / "n.json"
    p.write_text("123", encoding="utf-8")
    with pytest.raises(InventoryLoadError):
        JsonInventoryRepository(p).load()


def test_sqlite_load(tmp_path):
    p = tmp_path / "inv.sqlite"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE taskbots (nombre TEXT, tipo_interaccion TEXT, frecuencia TEXT, riesgo TEXT)")
    conn.execute("INSERT INTO taskbots VALUES ('Bot SQL','database','mensual','alto')")
    conn.commit(); conn.close()
    bots, errors = SqliteInventoryRepository(p).load()
    assert len(bots) == 1 and errors == []


def test_sqlite_tabla_inexistente(tmp_path):
    p = tmp_path / "inv.sqlite"
    sqlite3.connect(p).close()
    with pytest.raises(InventoryLoadError):
        SqliteInventoryRepository(p).load()


def test_sqlite_archivo_inexistente(tmp_path):
    with pytest.raises(InventoryLoadError):
        SqliteInventoryRepository(tmp_path / "no.sqlite").load()


def test_txt_archivo_inexistente(tmp_path):
    with pytest.raises(InventoryLoadError):
        TxtInventoryRepository(tmp_path / "no.txt").load()


def test_txt_sin_bloques_validos(tmp_path):
    p = tmp_path / "vacio.txt"
    p.write_text("solo texto sin estructura\n", encoding="utf-8")
    with pytest.raises(InventoryLoadError):
        TxtInventoryRepository(p).load()


def test_factory_por_extension(tmp_path):
    assert isinstance(repository_for("x.csv"), CsvInventoryRepository)
    assert isinstance(repository_for("x.json"), JsonInventoryRepository)
    assert isinstance(repository_for("x.sqlite"), SqliteInventoryRepository)
    assert isinstance(repository_for("x.txt"), TxtInventoryRepository)


def test_factory_extension_no_soportada():
    with pytest.raises(InventoryLoadError):
        repository_for("x.xml")
