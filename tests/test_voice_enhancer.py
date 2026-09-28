"""Tests unitarios para el procesador de realce vocal (VoiceEnhancer)."""

from pathlib import Path

import numpy as np
import pytest

from app.audio.loudness import LoudnessProcessor
from app.audio.voice_enhancer import VoiceEnhancer


@pytest.fixture
def noisy_voice_simulation_wav(tmp_path: Path) -> Path:
    """Genera audio con rumble subsónico a 30Hz + tono vocal a 1000Hz."""
    wav_path = tmp_path / "noisy_voice.wav"
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    rumble_30hz = 0.4 * np.sin(2 * np.pi * 30 * t)
    vocal_1000hz = 0.4 * np.sin(2 * np.pi * 1000 * t)
    combined = (rumble_30hz + vocal_1000hz).astype(np.float32)
    return LoudnessProcessor.write_wav(wav_path, sr, combined)


def test_voice_enhancer_filters_rumble(noisy_voice_simulation_wav: Path, tmp_path: Path):
    out_wav = tmp_path / "enhanced_voice.wav"
    VoiceEnhancer.enhance_voice_track(noisy_voice_simulation_wav, out_wav)

    assert out_wav.exists()
    sr, data = LoudnessProcessor.read_wav(out_wav)
    assert sr == 44100
    assert len(data) > 0
    assert not np.isnan(data).any()
    assert not np.isinf(data).any()
