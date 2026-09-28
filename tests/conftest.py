"""Fixtures globales para pruebas de integración con medios sintéticos."""

import subprocess
from pathlib import Path

import pytest

from app.utils.ffmpeg import FFmpegManager


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """
    Genera un archivo MP4 sintético de 2 segundos (320x240 a 30fps con tono senoidal de 440Hz)
    utilizando el binario descubierto de FFmpeg.
    """
    session_tmp = tmp_path_factory.mktemp("media")
    video_path = session_tmp / "fixture_video.mp4"

    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=2:size=320x240:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "64k",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Fallo al generar video sintético: {result.stderr.decode()}")

    return video_path
