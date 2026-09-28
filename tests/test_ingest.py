"""Tests de integración para el orquestador de ingesta de medios."""

from pathlib import Path

from app.core.ingest import ingest_media
from app.core.project import ProjectManager


def test_ingest_media_pipeline(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "my_project"
    ProjectManager.create_project(proj_dir, project_name="Ingest Test", profile="social")

    stages_logged = []

    def _cb(stage: str, progress: float):
        stages_logged.append((stage, progress))

    result = ingest_media(
        project_dir=proj_dir,
        source_video_path=synthetic_video,
        copy_raw=True,
        progress_callback=_cb,
    )

    # 1. Verificar retorno
    assert result["file_name"] == "fixture_video.mp4"
    assert (proj_dir / "raw" / "fixture_video.mp4").exists()
    assert (proj_dir / "analysis" / "media.json").exists()
    assert (proj_dir / "proxies" / "proxy_fixture_video.mp4").exists()
    assert (proj_dir / "cache" / "audio.wav").exists()

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert len(manifest["media_files"]) == 1
    assert manifest["media_files"][0]["file_name"] == "fixture_video.mp4"

    # 3. Verificar etapas reportadas
    assert len(stages_logged) > 0
    assert any(s[0] == "completed" for s in stages_logged)
