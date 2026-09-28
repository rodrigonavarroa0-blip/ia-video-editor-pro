"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 9 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app
from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project

runner = CliRunner()


def test_qa_render_without_subtitles(synthetic_video: Path, tmp_path: Path):
    """Prueba que el renderizado final funcione correctamente sin subtítulos quemados."""
    proj_dir = tmp_path / "qa_render_no_subs"
    ProjectManager.create_project(proj_dir, project_name="No Subs Render", profile="social")

    ingest_media(proj_dir, synthetic_video)
    create_editorial_plan_for_project(proj_dir, force_heuristic=True)

    metadata = render_final_video_for_project(proj_dir, preset="preview", burn_subtitles=False)
    assert metadata["burned_subtitles"] is False
    assert (proj_dir / "renders" / "final_video.mp4").exists()


def test_qa_cli_render_command(synthetic_video: Path, tmp_path: Path):
    """Prueba el comando CLI iva render."""
    proj_dir = str(tmp_path / "cli_render_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])
    runner.invoke(app, ["plan-edit", proj_dir, "--offline"])

    res = runner.invoke(app, ["render", proj_dir, "--preset", "preview", "--no-subs"])
    assert res.exit_code == 0
    assert "Render Final Completado Exitosamente" in res.stdout
