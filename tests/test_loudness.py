"""Tests unitarios para el procesador de sonoridad EBU R128 (LoudnessProcessor)."""

from pathlib import Path

import numpy as np
import pytest

from app.audio.loudness import LoudnessProcessor


@pytest.fixture
def loud_sine_wav(tmp_path: Path) -> Path:
    """Genera un archivo WAV con onda senoidal de 440Hz a -6 dBFS."""
    wav_path = tmp_path / "loud_sine.wav"
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    # 0.5 de amplitud = -6 dBFS
    audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return LoudnessProcessor.write_wav(wav_path, sr, audio)


def test_measure_loudness_properties(loud_sine_wav: Path):
    metrics = LoudnessProcessor.measure_loudness(loud_sine_wav, target_lufs=-14.0)

    assert isinstance(metrics.integrated_lufs, float)
    assert metrics.integrated_lufs > -40.0
    assert metrics.true_peak_db <= 0.0
    assert metrics.target_lufs == -14.0


def test_normalize_audio_to_target_lufs(loud_sine_wav: Path, tmp_path: Path):
    out_wav = tmp_path / "normalized_sine.wav"
    _, final_metrics = LoudnessProcessor.normalize_audio(
        loud_sine_wav,
        out_wav,
        target_lufs=-14.0,
        max_true_peak_db=-1.0,
    )

    assert out_wav.exists()
    # La sonoridad final debe estar a -14 LUFS (+- 0.8 LUFS de tolerancia estándar)
    assert abs(final_metrics.integrated_lufs - (-14.0)) < 0.8
    # El True Peak no debe sobrepasar el techo de -1.0 dBTP
    assert final_metrics.true_peak_db <= -0.9
