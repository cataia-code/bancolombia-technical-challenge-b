"""Tests de la interfaz CLI (Typer)."""

from pathlib import Path

from typer.testing import CliRunner

from taskbot_advisor.interface.cli import app

runner = CliRunner()
TXT = (Path(__file__).resolve().parents[2] / "data" / "ejemplo_50_taskbots_prueba.txt").as_posix()


def test_cli_analyze_genera_reportes(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKBOT_REPORTS_DIR", str(tmp_path))
    result = runner.invoke(app, ["analyze", TXT, "--run-id", "cli_test"])
    assert result.exit_code == 0
    assert "cli_test" in result.stdout
    assert (tmp_path / "cli_test" / "reporte.json").exists()
    assert (tmp_path / "cli_test" / "reporte.html").exists()


def test_cli_quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKBOT_REPORTS_DIR", str(tmp_path))
    result = runner.invoke(app, ["analyze", TXT, "--run-id", "q", "--quiet"])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_cli_archivo_inexistente_falla():
    result = runner.invoke(app, ["analyze", "no/existe.csv"])
    assert result.exit_code != 0
