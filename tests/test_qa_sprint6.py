"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 6 (§107)."""

from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from app.audio.loudness import LoudnessProcessor
from app.cli.main import app

runner = CliRunner()


def test_qa_pure_silence_audio_loudness(tmp_path: Path):
    """Prueba que el procesador de sonoridad maneje silencio digital absoluto (0.0) sin crash."""
    wav_path = tmp_path / "zero_silence.wav"
    sr = 44100
    zero_audio = np.zeros(sr * 2, dtype=np.float32)
    LoudnessProcessor.write_wav(wav_path, sr, zero_audio)

    metrics = LoudnessProcessor.measure_loudness(wav_path, target_lufs=-14.0)
    assert metrics.integrated_lufs <= -65.0

    out_norm = tmp_path / "norm_zero.wav"
    LoudnessProcessor.normalize_audio(wav_path, out_norm, target_lufs=-14.0)
    assert out_norm.exists()


def test_qa_clipping_audio_normalization(tmp_path: Path):
    """Prueba que un audio hiper-saturado se normalice a -14 LUFS con True Peak <= -1.0 dBTP."""
    wav_path = tmp_path / "clipped_audio.wav"
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    # Onda cuadrada hiper-saturada
    square_audio = np.sign(np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    LoudnessProcessor.write_wav(wav_path, sr, square_audio)

    out_norm = tmp_path / "norm_clipped.wav"
    _, final_metrics = LoudnessProcessor.normalize_audio(
        wav_path,
        out_norm,
        target_lufs=-14.0,
        max_true_peak_db=-1.0,
    )

    assert out_norm.exists()
    assert abs(final_metrics.integrated_lufs - (-14.0)) < 1.0
    assert final_metrics.true_peak_db <= -0.95


def test_qa_cli_audio_commands(synthetic_video: Path, tmp_path: Path):
    """Prueba la ejecución en CLI de los comandos measure-audio y enhance-audio."""
    proj_dir = str(tmp_path / "cli_audio_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])

    audio_file = str(tmp_path / "cli_audio_proj" / "cache" / "audio.wav")

    # 1. iva measure-audio
    res_measure = runner.invoke(app, ["measure-audio", audio_file, "--target", "-14.0"])
    assert res_measure.exit_code == 0
    assert "Medición Acústica EBU R128" in res_measure.stdout

    # 2. iva enhance-audio
    res_enhance = runner.invoke(app, ["enhance-audio", proj_dir, "--target", "-14.0"])
    assert res_enhance.exit_code == 0
    assert "Audio Masterizado Exitosamente" in res_enhance.stdout
