"""Tests unitarios para el wrapper de FFmpeg."""

import os

import pytest

from app.utils.ffmpeg import FFmpegError, FFmpegManager


def test_ffmpeg_discovery():
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    assert ffmpeg_exe is not None
    assert os.path.exists(ffmpeg_exe)


def test_ffprobe_discovery():
    ffprobe_exe = FFmpegManager.get_ffprobe_path()
    # ffprobe puede o no estar en PATH del sistema; si no está, has_ffprobe es False
    if ffprobe_exe is not None:
        assert os.path.exists(ffprobe_exe)
        assert FFmpegManager.has_ffprobe() is True
    else:
        assert FFmpegManager.has_ffprobe() is False


def test_encoder_selection():
    encoder = FFmpegManager.get_optimal_video_encoder()
    assert encoder in ["h264_videotoolbox", "libx264"]


def test_run_command_invalid():
    with pytest.raises(FFmpegError):
        FFmpegManager.run_command(["-invalid_argument_that_fails"])
