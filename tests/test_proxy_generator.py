"""Tests unitarios para ProxyGenerator."""

from pathlib import Path

from app.analyzers.media_probe import MediaProbe
from app.render.proxy_generator import ProxyGenerator


def test_generate_proxy(synthetic_video: Path, tmp_path: Path):
    proxy_output = tmp_path / "proxy.mp4"
    generated = ProxyGenerator.generate_proxy(
        source_path=synthetic_video,
        output_path=proxy_output,
        max_dimension=1280,
    )

    assert generated.exists()
    assert generated.stat().st_size > 0

    # Probar que el proxy sea reproducible y válido
    probe = MediaProbe.probe(generated)
    assert probe.has_video is True
    assert probe.primary_video is not None
    assert probe.primary_video.width % 2 == 0
    assert probe.primary_video.height % 2 == 0


def test_extract_audio_wav(synthetic_video: Path, tmp_path: Path):
    wav_output = tmp_path / "audio.wav"
    extracted = ProxyGenerator.extract_audio_wav(
        source_path=synthetic_video,
        output_wav_path=wav_output,
        sample_rate=44100,
        channels=1,
    )

    assert extracted.exists()
    assert extracted.stat().st_size > 0

    # Probar que sea un archivo WAV válido inspeccionable
    probe = MediaProbe.probe(extracted)
    assert probe.has_audio is True
    assert probe.primary_audio is not None
    assert probe.primary_audio.sample_rate == 44100
