"""Tests de integración para el orquestador de renderizado final (render_final_video_for_project)."""

from pathlib import Path

from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project


def test_render_orchestrator_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "render_proj"
    ProjectManager.create_project(proj_dir, project_name="Render Master Test", profile="social")

    # Ingestar y planificar
    ingest_media(proj_dir, synthetic_video)
    create_editorial_plan_for_project(proj_dir, force_heuristic=True)

    # Renderizar video final
    metadata = render_final_video_for_project(proj_dir, preset="preview", burn_subtitles=False)
    assert metadata["output_file"] is not None

    # 1. Verificar archivos en disco (§4.3)
    final_video = proj_dir / "renders" / "final_video.mp4"
    render_meta = proj_dir / "renders" / "render_metadata.json"
    assert final_video.exists()
    assert render_meta.exists()
    assert final_video.stat().st_size > 1000

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["rendered"] is True
    assert manifest["final_video_path"] == "renders/final_video.mp4"
    assert manifest["final_video_size_mb"] > 0.0
