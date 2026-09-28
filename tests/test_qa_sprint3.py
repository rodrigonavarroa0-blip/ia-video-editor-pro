"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 3 (§107)."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from app.analyzers.scene_detector import SceneDetector
from app.analyzers.silence_detector import SilenceDetector
from app.cli.main import app
from app.models.editorial import SilenceSeverity
from app.utils.ffmpeg import FFmpegManager

runner = CliRunner()


def test_qa_continuous_video_single_scene(tmp_path: Path):
    """Prueba con video de color estático continuo sin ningún cambio de plano."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    vid_path = tmp_path / "static_green.mp4"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=green:duration=3:size=320x240:rate=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(vid_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    scenes = SceneDetector.detect_scenes(vid_path)
    assert len(scenes) == 1
    assert scenes[0].start == 0.0
    assert 2.8 <= scenes[0].duration <= 3.2


def test_qa_continuous_loud_audio_no_silence(tmp_path: Path):
    """Prueba con audio continuo a volumen constante (sin pausas)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    wav_path = tmp_path / "continuous_beep.wav"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-acodec", "pcm_s16le", str(wav_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    intervals = SilenceDetector.detect_silence(wav_path, threshold_db=-38.0)
    assert len(intervals) == 0


def test_qa_complete_silence_audio_interval(tmp_path: Path):
    """Prueba con audio 100% en silencio absoluto."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    silent_wav = tmp_path / "all_silent.wav"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "3",
        "-acodec", "pcm_s16le", str(silent_wav),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    intervals = SilenceDetector.detect_silence(silent_wav, threshold_db=-38.0)
    assert len(intervals) == 1
    assert intervals[0].severity == SilenceSeverity.CUT_AGGRESSIVE
    assert 2.8 <= intervals[0].duration <= 3.1


def test_qa_cli_sprint3_commands(synthetic_video: Path, tmp_path: Path):
    """Prueba la invocación de los comandos detect-scenes, detect-silence y analyze en CLI."""
    # 1. detect-scenes
    res_scenes = runner.invoke(app, ["detect-scenes", str(synthetic_video)])
    assert res_scenes.exit_code == 0
    assert "Detección de Escenas" in res_scenes.stdout

    # 2. Ingestar y extraer audio
    proj_dir = str(tmp_path / "cli_sprint3_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])

    audio_file = str(tmp_path / "cli_sprint3_proj" / "cache" / "audio.wav")
    res_silence = runner.invoke(app, ["detect-silence", audio_file])
    assert res_silence.exit_code == 0
    assert "Análisis de Silencios" in res_silence.stdout

    # 3. analyze
    res_analyze = runner.invoke(app, ["analyze", proj_dir])
    assert res_analyze.exit_code == 0
    assert "Análisis unificado completado con éxito" in res_analyze.stdout
