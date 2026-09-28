"""Tests unitarios para el procesador de auto-ducking musical (DuckingProcessor)."""

from pathlib import Path

import numpy as np

from app.audio.ducking import DuckingProcessor
from app.audio.loudness import LoudnessProcessor


def test_ducking_envelope_generation():
    sr = 44100
    total_samples = sr * 4  # 4 segundos
    # Habla entre 1.0s y 2.5s
    speech = [(1.0, 2.5)]

    env = DuckingProcessor.generate_ducking_envelope(
        total_samples=total_samples,
        sample_rate=sr,
        speech_intervals=speech,
        base_gain_db=-4.0,
        ducked_gain_db=-16.0,
        attack_ms=100.0,
        release_ms=200.0,
    )

    # 1. En t=0.5s (sin voz) el volumen debe ser alto (base)
    idx_05 = int(0.5 * sr)
    base_linear = 10.0 ** (-4.0 / 20.0)
    assert abs(env[idx_05] - base_linear) < 0.05

    # 2. En t=1.8s (durante la voz) el volumen debe estar atenuado (ducked)
    idx_18 = int(1.8 * sr)
    ducked_linear = 10.0 ** (-16.0 / 20.0)
    assert abs(env[idx_18] - ducked_linear) < 0.05

    # 3. En t=3.5s (después de la voz) el volumen debe haber recuperado el nivel base
    idx_35 = int(3.5 * sr)
    assert abs(env[idx_35] - base_linear) < 0.05


def test_mix_voice_and_music(tmp_path: Path):
    sr = 44100
    dur = 2.0
    t = np.linspace(0, dur, int(sr * dur))

    voice_audio = (0.5 * np.sin(2 * np.pi * 500 * t)).astype(np.float32)
    music_audio = (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

    voice_wav = LoudnessProcessor.write_wav(tmp_path / "voice.wav", sr, voice_audio)
    music_wav = LoudnessProcessor.write_wav(tmp_path / "music.wav", sr, music_audio)
    out_mixed = tmp_path / "mixed.wav"

    DuckingProcessor.mix_voice_and_music(voice_wav, music_wav, out_mixed, speech_intervals=[(0.5, 1.5)])
    assert out_mixed.exists()
    sr_m, data_m = LoudnessProcessor.read_wav(out_mixed)
    assert sr_m == sr
    assert len(data_m) == len(voice_audio)
