"""Tests unitarios para el detector de silencios acústicos."""

import subprocess
from pathlib import Path

import pytest

from app.analyzers.silence_detector import SilenceDetector
from app.models.editorial import SilenceSeverity
from app.utils.ffmpeg import FFmpegManager


@pytest.fixture
def tone_silence_tone_wav(tmp_path: Path) -> Path:
    """Genera un archivo WAV con: 1s tono (440Hz), 1s silencio (anullsrc), 1s tono (880Hz)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    wav_path = tmp_path / "tone_silence_tone.wav"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono,atrim=duration=1",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=1",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]",
        "-map", "[a]",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        str(wav_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return wav_path


def test_detect_silence_interval(tone_silence_tone_wav: Path):
    intervals = SilenceDetector.detect_silence(tone_silence_tone_wav, threshold_db=-35.0)

    assert len(intervals) >= 1
    # El silencio de 1 segundo debe ubicarse alrededor de 1.0s a 2.0s
    silence = intervals[0]
    assert 0.9 <= silence.start <= 1.1
    assert 1.9 <= silence.end <= 2.1
    assert silence.duration >= 0.9
    assert silence.severity == SilenceSeverity.CUT_AGGRESSIVE
