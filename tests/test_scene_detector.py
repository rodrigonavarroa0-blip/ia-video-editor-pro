"""Tests unitarios para el detector de escenas con OpenCV."""

import subprocess
from pathlib import Path

import pytest

from app.analyzers.scene_detector import SceneDetector
from app.utils.ffmpeg import FFmpegManager


@pytest.fixture
def two_scene_video(tmp_path: Path) -> Path:
    """Genera un video sintético con 2 planos contrastados (1s rojo y 1s azul)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    vid_path = tmp_path / "two_scenes.mp4"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=red:duration=1:size=320x240:rate=30",
        "-f", "lavfi", "-i", "color=c=blue:duration=1:size=320x240:rate=30",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(vid_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return vid_path


def test_detect_scenes_two_cuts(two_scene_video: Path):
    scenes = SceneDetector.detect_scenes(two_scene_video, threshold=0.25, min_scene_duration_sec=0.4)

    assert len(scenes) >= 2
    assert scenes[0].start == 0.0
    assert scenes[0].end >= 0.9
    assert scenes[1].start >= 0.9
    assert scenes[1].end <= 2.1
