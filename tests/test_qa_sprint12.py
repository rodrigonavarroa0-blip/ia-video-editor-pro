"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 12 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app

runner = CliRunner()


def test_qa_cli_package_command(tmp_path: Path):
    """Prueba el comando CLI iva package en modo standalone."""
    out_dir = str(tmp_path / "cli_pkg_out")
    res = runner.invoke(app, ["package", "--output-dir", out_dir, "--skip-dmg"])
    assert res.exit_code == 0
    assert "Bundle macOS generado" in res.stdout
    assert (tmp_path / "cli_pkg_out" / "IA Video Editor Pro.app").exists()


def test_qa_cli_package_help():
    """Prueba la ayuda del comando iva package."""
    res = runner.invoke(app, ["package", "--help"])
    assert res.exit_code == 0
    assert "Empaqueta la aplicación standalone para macOS" in res.stdout
