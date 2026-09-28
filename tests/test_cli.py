"""Tests unitarios para la CLI de Typer."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "IA Video Editor Pro" in result.stdout


def test_cli_info():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Estado del Sistema" in result.stdout
    assert "gemini-3.7-flash" in result.stdout


def test_cli_init_project(tmp_path: Path):
    target = str(tmp_path / "cli_test_proj")
    result = runner.invoke(app, ["init-project", target, "--name", "Test CLI Project", "--profile", "youtube"])
    assert result.exit_code == 0
    assert "creado exitosamente" in result.stdout
    assert (tmp_path / "cli_test_proj" / "project.json").exists()


def test_cli_probe(synthetic_video: Path):
    result = runner.invoke(app, ["probe", str(synthetic_video)])
    assert result.exit_code == 0
    assert "Inspección Técnica" in result.stdout
    assert "fixture_video.mp4" in result.stdout


def test_cli_ingest(synthetic_video: Path, tmp_path: Path):
    proj_dir = str(tmp_path / "cli_ingest_proj")
    runner.invoke(app, ["init-project", proj_dir])
    result = runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])
    assert result.exit_code == 0
    assert "Ingesta completada con éxito" in result.stdout
