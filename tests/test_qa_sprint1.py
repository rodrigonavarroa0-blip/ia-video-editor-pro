"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 1 (§107)."""

import hashlib
import subprocess
from pathlib import Path
import pytest
from app.analyzers.media_probe import MediaProbe
from app.core.ingest import ingest_media
from app.core.project import ProjectManager
from app.render.proxy_generator import ProxyGenerator
from app.utils.ffmpeg import FFmpegManager


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_qa_vertical_video(tmp_path: Path):
    """Prueba de robustez: Ingesta de video vertical nativo 9:16 (1080x1920)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    vertical_video = tmp_path / "vertical_source.mp4"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=1080x1920:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac", str(vertical_video),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    probe = MediaProbe.probe(vertical_video)
    assert probe.primary_video is not None
    assert probe.primary_video.width == 1080
    assert probe.primary_video.height == 1920
    assert probe.primary_video.aspect_ratio == "9:16"

    proxy_out = tmp_path / "proxy_vertical.mp4"
    ProxyGenerator.generate_proxy(vertical_video, proxy_out, probe)
    assert proxy_out.exists()
    proxy_probe = MediaProbe.probe(proxy_out)
    assert proxy_probe.primary_video.width == 720
    assert proxy_probe.primary_video.height == 1280
    assert proxy_probe.primary_video.width % 2 == 0


def test_qa_square_video(tmp_path: Path):
    """Prueba de robustez: Ingesta de video cuadrado 1:1 (1080x1080)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    square_video = tmp_path / "square_source.mp4"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=1080x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac", str(square_video),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    probe = MediaProbe.probe(square_video)
    assert probe.primary_video.aspect_ratio == "1:1"

    proxy_out = tmp_path / "proxy_square.mp4"
    ProxyGenerator.generate_proxy(square_video, proxy_out, probe)
    assert proxy_out.exists()
    proxy_probe = MediaProbe.probe(proxy_out)
    assert proxy_probe.primary_video.width % 2 == 0
    assert proxy_probe.primary_video.height % 2 == 0


def test_qa_video_without_audio(tmp_path: Path):
    """Prueba de robustez: Video sin pista de audio (an)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    video_no_audio = tmp_path / "video_no_audio.mp4"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
        "-c:v", "libx264", "-an", str(video_no_audio),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    probe = MediaProbe.probe(video_no_audio)
    assert probe.has_video is True
    assert probe.has_audio is False
    assert probe.primary_audio is None

    proj_dir = tmp_path / "project_no_audio"
    ProjectManager.create_project(proj_dir, "No Audio Project", profile="social")
    res = ingest_media(proj_dir, video_no_audio)
    assert res["proxy_path"] is not None
    assert res["audio_path"] is None


def test_qa_audio_only_file(tmp_path: Path):
    """Prueba de robustez: Archivo de solo audio WAV."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    audio_only = tmp_path / "sound.wav"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:a", "pcm_s16le", str(audio_only),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    probe = MediaProbe.probe(audio_only)
    assert probe.has_video is False
    assert probe.has_audio is True
    assert probe.primary_video is None
    assert probe.primary_audio is not None

    proj_dir = tmp_path / "project_audio_only"
    ProjectManager.create_project(proj_dir, "Audio Project", profile="podcast")
    res = ingest_media(proj_dir, audio_only)
    assert res["proxy_path"] is None
    assert res["audio_path"] is not None


def test_qa_paths_with_spaces_and_special_chars(tmp_path: Path):
    """Prueba de robustez: Rutas con espacios, tildes y caracteres especiales."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    special_video = tmp_path / "video con espacios y tildes (acción) & símbolos.mp4"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-c:a", "aac", str(special_video),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    proj_dir = tmp_path / "Proyecto Con Espacios"
    ProjectManager.create_project(proj_dir, "Espacios Test", profile="social")
    res = ingest_media(proj_dir, special_video)
    assert Path(res["raw_path"]).exists()
    assert Path(res["proxy_path"]).exists()
    assert Path(res["audio_path"]).exists()


def test_qa_non_destructive_immutability(tmp_path: Path):
    """Prueba de inmutabilidad: El archivo RAW original no debe sufrir ninguna alteración."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    raw_source = tmp_path / "original_source.mp4"

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac", str(raw_source),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    hash_before = _sha256(raw_source)

    proj_dir = tmp_path / "immutability_project"
    ProjectManager.create_project(proj_dir, "Immutability Project", profile="social")
    ingest_media(proj_dir, raw_source)

    hash_after = _sha256(raw_source)
    assert hash_before == hash_after, "El archivo RAW original fue modificado de forma destructiva!"


def test_qa_corrupted_file(tmp_path: Path):
    """Prueba de archivo corrupto: Manejo adecuado de errores sin crashear."""
    corrupt_file = tmp_path / "corrupt_video.mp4"
    corrupt_file.write_bytes(b"Este no es un archivo de video valido, datos corruptos...")

    with pytest.raises((RuntimeError, ValueError)):
        MediaProbe.probe(corrupt_file)
