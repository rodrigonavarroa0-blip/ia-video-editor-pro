"""Tests de integración para el pipeline orquestador de audio."""

from pathlib import Path

from app.core.audio_pipeline import process_project_audio
from app.core.ingest import ingest_media
from app.core.project import ProjectManager


def test_process_project_audio_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "audio_pipeline_proj"
    ProjectManager.create_project(proj_dir, project_name="Audio Test", profile="social")

    # Ingestar
    ingest_media(proj_dir, synthetic_video)

    # Masterizar audio
    metrics = process_project_audio(proj_dir, target_lufs=-14.0)
    assert metrics is not None

    # 1. Verificar archivos en disco (§4.3)
    assert (proj_dir / "cache" / "audio_enhanced.wav").exists()
    assert (proj_dir / "cache" / "audio_master.wav").exists()
    assert (proj_dir / "analysis" / "audio_metrics_raw.json").exists()
    assert (proj_dir / "analysis" / "audio_metrics.json").exists()

    # 2. Verificar métricas y manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["audio_processed"] is True
    assert manifest["audio_master_path"] == "cache/audio_master.wav"
    assert abs(manifest["final_lufs"] - (-14.0)) < 1.0
