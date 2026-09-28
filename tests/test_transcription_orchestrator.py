"""Tests de integración para el orquestador de transcripción de proyectos."""

from pathlib import Path

from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.transcription import transcribe_project


def test_transcribe_project_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "transcribe_project_test"
    ProjectManager.create_project(proj_dir, project_name="Transcribe Test")

    # 1. Ingestar medio
    ingest_media(proj_dir, synthetic_video)

    # 2. Transcribir
    doc = transcribe_project(proj_dir, model_size="tiny")

    assert (proj_dir / "analysis" / "transcript.json").exists()

    # 3. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["transcript_ready"] is True
    assert manifest["transcript_path"] == "analysis/transcript.json"
    assert manifest["word_count"] == doc.word_count
