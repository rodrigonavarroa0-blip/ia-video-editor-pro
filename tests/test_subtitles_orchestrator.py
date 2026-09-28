"""Tests de integración para el orquestador de subtítulos (generate_subtitles_for_project)."""

from pathlib import Path

from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.subtitles import generate_subtitles_for_project
from app.core.transcription import transcribe_project


def test_subtitles_orchestrator_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "subtitles_proj"
    ProjectManager.create_project(proj_dir, project_name="Subtitles Test", profile="social")

    # Ingestar y transcribir
    ingest_media(proj_dir, synthetic_video)
    transcribe_project(proj_dir, model_size="tiny")

    # Generar subtítulos
    subs = generate_subtitles_for_project(proj_dir, style="hormozi", max_words=3)

    # 1. Verificar archivos en renders/ (§4.3)
    assert subs["ass"].exists()
    assert subs["srt"].exists()
    assert subs["vtt"].exists()
    assert (proj_dir / "renders" / "subtitles.ass").exists()

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["subtitles_ready"] is True
    assert manifest["subtitles_style"] == "hormozi"
    assert manifest["subtitles_ass_path"] == "renders/subtitles.ass"
