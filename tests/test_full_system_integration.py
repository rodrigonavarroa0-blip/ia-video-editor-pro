"""Prueba de Integración Completa y Conexiones Generales del Sistema (E2E Master Test).

Valida la conexión y flujo de datos ininterrumpido a través de:
- Sprint 0 (Foundation, Pydantic, Configuración, Logging)
- Sprint 1 (Media Ingest, MediaProbe, Proxies 720p, Extracción WAV)
- Sprint 2 (faster-whisper, Timestamps por palabra, WPM, Filler Words)
- Sprint 3 (Scene Detection con OpenCV, Silence Analysis Multinivel, AnalysisResult)
- Sprint 4 (Editorial Engine, Hook Score, Retention, Redundancy, edit_plan.json)
- Sprint 5 (Vision Tracking, Face Detection, Smart Reframing 9:16, reframing.json)
- Sprint 6 (Audio Engine, LUFS EBU R128, Voice Enhance, audio_metrics.json)
- Sprint 7 (Subtitle Engine, Kinetic ASS, Sidecar SRT/VTT, subtitles.ass)
- Sprint 8 (Virtual Timeline, CMX 3600 EDL, FCPXML, OpenTimelineIO .otio)
- Sprint 9 (Final Render Engine, Conform to RAW, VideoToolbox/NVENC, final_video.mp4)
- CLI e IPC Event Streaming
"""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli.main import app
from app.core.analysis import run_full_analysis
from app.core.audio_pipeline import process_project_audio
from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project
from app.core.subtitles import generate_subtitles_for_project
from app.core.timeline import build_and_export_timeline_for_project
from app.core.transcription import transcribe_project
from app.core.vision import run_vision_tracking_for_project
from app.utils.ffmpeg import FFmpegManager

runner = CliRunner()


@pytest.fixture
def multi_scene_audio_video(tmp_path: Path) -> Path:
    """Genera un archivo de video complejo con 2 planos de color y audio con tono y silencios."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    vid_path = tmp_path / "complex_e2e_video.mp4"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=black:duration=1.5:size=640x360:rate=30",
        "-f", "lavfi", "-i", "color=c=yellow:duration=1.5:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono,atrim=duration=1.0",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=1.0",
        "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a][3:a][4:a]concat=n=3:v=0:a=1[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(vid_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return vid_path


def test_full_system_connections_e2e(multi_scene_audio_video: Path, tmp_path: Path):
    """Test maestro de extremo a extremo que valida la conexión total de todos los módulos."""
    proj_dir = tmp_path / "e2e_master_project"

    # 1. Sprint 0: Inicialización
    created_path = ProjectManager.create_project(proj_dir, project_name="E2E Master Test", profile="social")
    assert created_path.exists()
    assert (proj_dir / "project.json").exists()

    # 2. Sprint 1: Ingesta
    ingest_result = ingest_media(proj_dir, multi_scene_audio_video)
    assert ingest_result["raw_path"] is not None
    assert (proj_dir / "raw" / "complex_e2e_video.mp4").exists()
    assert (proj_dir / "proxies" / "proxy_complex_e2e_video.mp4").exists()
    assert (proj_dir / "cache" / "audio.wav").exists()
    assert (proj_dir / "analysis" / "media.json").exists()

    # 3. Sprint 2: Transcripción
    doc = transcribe_project(proj_dir, model_size="tiny", language="es")
    assert (proj_dir / "analysis" / "transcript.json").exists()
    assert doc.duration_seconds >= 2.8

    # 4. Sprint 3: Análisis Integral (Escenas + Silencios)
    analysis_result = run_full_analysis(proj_dir)
    assert analysis_result is not None
    assert (proj_dir / "analysis" / "scenes.json").exists()
    assert (proj_dir / "analysis" / "silence.json").exists()
    assert (proj_dir / "analysis" / "analysis_summary.json").exists()

    # 5. Sprint 4: Planificación Editorial Inteligente
    plan = create_editorial_plan_for_project(proj_dir, force_heuristic=True)
    assert (proj_dir / "analysis" / "edit_plan.json").exists()
    assert len(plan.decisions) >= 1

    # 6. Sprint 5: Visión y Smart Reframing 9:16
    tracks, keyframes = run_vision_tracking_for_project(proj_dir, target_format="9:16")
    assert isinstance(tracks, list)
    assert (proj_dir / "analysis" / "face_tracking.json").exists()
    assert (proj_dir / "analysis" / "reframing.json").exists()

    # 7. Sprint 6: Audio Engine y Masterización EBU R128
    audio_metrics = process_project_audio(proj_dir, target_lufs=-14.0)
    assert audio_metrics is not None
    assert (proj_dir / "cache" / "audio_enhanced.wav").exists()
    assert (proj_dir / "cache" / "audio_master.wav").exists()
    assert (proj_dir / "analysis" / "audio_metrics.json").exists()

    # 8. Sprint 7: Subtitle Engine (Kinetic ASS + SRT + VTT)
    subs = generate_subtitles_for_project(proj_dir, style="hormozi")
    assert "ass" in subs
    assert (proj_dir / "renders" / "subtitles.ass").exists()
    assert (proj_dir / "renders" / "subtitles.srt").exists()
    assert (proj_dir / "renders" / "subtitles.vtt").exists()

    # 9. Sprint 8: Virtual Timeline y Formatos NLE (CMX 3600 EDL + FCPXML + OTIO)
    timeline_exports = build_and_export_timeline_for_project(proj_dir, fps=30.0, width=1080, height=1920)
    assert "edl" in timeline_exports
    assert (proj_dir / "timeline" / "virtual_timeline.json").exists()
    assert (proj_dir / "timeline" / "export.edl").exists()
    assert (proj_dir / "timeline" / "export.fcpxml").exists()
    assert (proj_dir / "timeline" / "export.otio").exists()

    # 10. Sprint 9: Final Render Engine (Conform to RAW + 9:16 Master Export)
    render_metadata = render_final_video_for_project(proj_dir, preset="preview", burn_subtitles=True)
    assert (proj_dir / "renders" / "final_video.mp4").exists()
    assert (proj_dir / "renders" / "render_metadata.json").exists()
    assert render_metadata["file_size_mb"] > 0.0

    # Validar integridad total del Manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["analysis_ready"] is True
    assert manifest["transcript_ready"] is True
    assert manifest["editorial_plan_ready"] is True
    assert manifest["vision_tracking_ready"] is True
    assert manifest["audio_processed"] is True
    assert manifest["subtitles_ready"] is True
    assert manifest["timeline_ready"] is True
    assert manifest["rendered"] is True
    assert manifest["final_video_path"] == "renders/final_video.mp4"
    assert manifest["scenes_count"] >= 2
    assert manifest["silence_intervals_count"] >= 1
    assert manifest["decisions_count"] == len(plan.decisions)
    assert manifest["reframing_keyframes_count"] == len(keyframes)


def test_cli_end_to_end_workflow(multi_scene_audio_video: Path, tmp_path: Path):
    """Test de flujo de trabajo completo invocando la CLI oficial (iva)."""
    proj_dir = str(tmp_path / "cli_e2e_project")

    # iva init-project
    res = runner.invoke(app, ["init-project", proj_dir, "--name", "CLI E2E", "--profile", "social"])
    assert res.exit_code == 0

    # iva probe
    res = runner.invoke(app, ["probe", str(multi_scene_audio_video)])
    assert res.exit_code == 0

    # iva ingest
    res = runner.invoke(app, ["ingest", proj_dir, str(multi_scene_audio_video)])
    assert res.exit_code == 0

    # iva transcribe
    res = runner.invoke(app, ["transcribe", proj_dir, "--model", "tiny"])
    assert res.exit_code == 0

    # iva analyze
    res = runner.invoke(app, ["analyze", proj_dir])
    assert res.exit_code == 0

    # iva plan-edit
    res = runner.invoke(app, ["plan-edit", proj_dir, "--offline"])
    assert res.exit_code == 0

    # iva reframe
    res = runner.invoke(app, ["reframe", proj_dir, "--format", "9:16"])
    assert res.exit_code == 0

    # iva enhance-audio
    res = runner.invoke(app, ["enhance-audio", proj_dir, "--target", "-14.0"])
    assert res.exit_code == 0

    # iva generate-subtitles
    res = runner.invoke(app, ["generate-subtitles", proj_dir, "--style", "hormozi"])
    assert res.exit_code == 0

    # iva build-timeline
    res = runner.invoke(app, ["build-timeline", proj_dir])
    assert res.exit_code == 0

    # iva render
    res = runner.invoke(app, ["render", proj_dir, "--preset", "preview"])
    assert res.exit_code == 0
