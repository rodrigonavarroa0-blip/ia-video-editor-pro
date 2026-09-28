"""Tests de integración para el orquestador de timeline y exportaciones NLE."""

from pathlib import Path

from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.timeline import build_and_export_timeline_for_project


def test_timeline_orchestrator_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "timeline_proj"
    ProjectManager.create_project(proj_dir, project_name="Timeline Test", profile="social")

    # Ingestar y generar plan editorial
    ingest_media(proj_dir, synthetic_video)
    create_editorial_plan_for_project(proj_dir, force_heuristic=True)

    # Construir y exportar timeline
    exports = build_and_export_timeline_for_project(proj_dir, fps=30.0, width=1080, height=1920)

    # 1. Verificar los 4 archivos en timeline/ (§4.3)
    assert exports["virtual_timeline"].exists()
    assert exports["edl"].exists()
    assert exports["fcpxml"].exists()
    assert exports["otio"].exists()

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["timeline_ready"] is True
    assert manifest["virtual_timeline_path"] == "timeline/virtual_timeline.json"
    assert manifest["edl_export_path"] == "timeline/export.edl"
    assert manifest["fcpxml_export_path"] == "timeline/export.fcpxml"
    assert manifest["otio_export_path"] == "timeline/export.otio"
    assert manifest["timeline_clips_count"] >= 1
