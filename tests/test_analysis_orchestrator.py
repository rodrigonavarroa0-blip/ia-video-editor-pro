"""Tests unitarios para el orquestador unificado de análisis."""

from pathlib import Path

from app.core.analysis import run_full_analysis
from app.core.ingest import ingest_media
from app.core.project import ProjectManager


def test_full_analysis_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "full_analysis_proj"
    ProjectManager.create_project(proj_dir, project_name="Full Analysis Test")
    ingest_media(proj_dir, synthetic_video)

    stages = []

    def _cb(stage: str, p: float):
        stages.append((stage, p))

    result = run_full_analysis(proj_dir, progress_callback=_cb)

    # 1. Verificar existencia de todos los JSONs reproducibles (§4.3)
    assert (proj_dir / "analysis" / "media.json").exists()
    assert (proj_dir / "analysis" / "transcript.json").exists()
    assert (proj_dir / "analysis" / "scenes.json").exists()
    assert (proj_dir / "analysis" / "silence.json").exists()
    assert (proj_dir / "analysis" / "analysis_summary.json").exists()

    # 2. Verificar resultado consolidado
    assert result.is_complete is True
    assert result.media_info.duration_seconds > 0.0
    assert len(result.scenes) >= 1

    # 3. Verificar project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["analysis_ready"] is True
    assert manifest["scenes_count"] == len(result.scenes)
