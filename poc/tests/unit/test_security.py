"""Tests for the input guardrails of the HTTP surface."""

import pytest

from taskbot_advisor.infrastructure.security import (
    SecurityError,
    resolve_inventory_path,
    validate_run_id,
)


def test_validate_run_id_ok():
    assert validate_run_id("cli_test-01") == "cli_test-01"
    assert validate_run_id(None) is None


@pytest.mark.parametrize("bad", ["../evil", "a/b", "run id", "-starts-dash", "x" * 65, ""])
def test_validate_run_id_rechaza_invalidos(bad):
    with pytest.raises(SecurityError):
        validate_run_id(bad)


def test_resolve_sin_root_devuelve_igual():
    assert resolve_inventory_path("data/x.csv", None) == "data/x.csv"


def test_resolve_con_root_contiene(tmp_path):
    (tmp_path / "inv.csv").write_text("nombre\nX\n", encoding="utf-8")
    resolved = resolve_inventory_path("inv.csv", str(tmp_path))
    assert resolved.endswith("inv.csv")
    assert str(tmp_path) in resolved


def test_resolve_con_root_bloquea_traversal(tmp_path):
    with pytest.raises(SecurityError):
        resolve_inventory_path("../../etc/passwd", str(tmp_path))


def test_resolve_con_root_bloquea_absoluta(tmp_path):
    # Una ruta absoluta se reinterpreta relativa al root; si escapa, se rechaza.
    with pytest.raises(SecurityError):
        resolve_inventory_path("/etc/passwd/../../../secret", str(tmp_path))
