"""Tests unitarios para MediaProbe."""

from pathlib import Path

import pytest

from app.analyzers.media_probe import MediaProbe


def test_media_probe_synthetic(synthetic_video: Path):
    media_info = MediaProbe.probe(synthetic_video)

    assert media_info.file_name == "fixture_video.mp4"
    assert media_info.has_video is True
    assert media_info.has_audio is True
    assert media_info.duration_seconds > 1.8

    assert media_info.primary_video is not None
    assert media_info.primary_video.width == 320
    assert media_info.primary_video.height == 240
    assert media_info.primary_video.fps == 30.0

    assert media_info.primary_audio is not None
    assert media_info.primary_audio.channels in [1, 2]


def test_media_probe_non_existent():
    with pytest.raises(FileNotFoundError):
        MediaProbe.probe(Path("/path/to/non_existent_file.mp4"))


def test_media_probe_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")
    with pytest.raises(ValueError):
        MediaProbe.probe(empty_file)
