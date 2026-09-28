"""Tests de integración para el orquestador de visión y smart reframing."""

from pathlib import Path

from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.vision import run_vision_tracking_for_project


def test_vision_tracking_orchestrator(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "vision_orchestrator_proj"
    ProjectManager.create_project(proj_dir, project_name="Vision Test", profile="social")

    # Ingestar video
    ingest_media(proj_dir, synthetic_video)

    # Ejecutar pipeline de visión
    tracks, keyframes = run_vision_tracking_for_project(proj_dir, target_format="9:16")
    assert isinstance(tracks, list)

    # 1. Verificar archivos JSON en disco (§4.3)
    assert (proj_dir / "analysis" / "face_tracking.json").exists()
    assert (proj_dir / "analysis" / "reframing.json").exists()

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["vision_tracking_ready"] is True
    assert manifest["reframing_path"] == "analysis/reframing.json"
    assert manifest["reframing_keyframes_count"] == len(keyframes)
