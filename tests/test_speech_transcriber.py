"""Tests unitarios para el motor de transcripción fonética."""

from pathlib import Path

from app.ai.speech_transcriber import (
    DEFAULT_FILLER_WORDS,
    SpeechTranscriber,
    calculate_speech_rate_wpm,
    clean_word_text,
)


def test_clean_word_text():
    assert clean_word_text("¡Hola,") == "hola"
    assert clean_word_text("¿Básicamente?") == "básicamente"
    assert clean_word_text("   tipo...  ") == "tipo"


def test_calculate_speech_rate_wpm():
    # 150 palabras en 60 segundos = 150 WPM
    assert calculate_speech_rate_wpm(150, 60.0) == 150.0
    # 10 palabras en 4 segundos = (10 / (4/60)) = 150 WPM
    assert calculate_speech_rate_wpm(10, 4.0) == 150.0
    assert calculate_speech_rate_wpm(0, 10.0) == 0.0
    assert calculate_speech_rate_wpm(10, 0.0) == 0.0


def test_filler_words_classification():
    fillers_es = DEFAULT_FILLER_WORDS["es"]
    assert "eh" in fillers_es
    assert "o sea" in fillers_es
    assert "básicamente" in fillers_es
    assert "importante" not in fillers_es


def test_speech_transcriber_synthetic(synthetic_video: Path, tmp_path: Path):
    """Transcribe un archivo de audio sintético (tono senoidal) verificando estructura."""
    from app.render.proxy_generator import ProxyGenerator
    wav_path = tmp_path / "test_tone.wav"
    ProxyGenerator.extract_audio_wav(synthetic_video, wav_path)

    # Usar modelo tiny/small para velocidad de test
    doc = SpeechTranscriber.transcribe(wav_path, model_size="tiny", language="es")

    assert doc.language is not None
    assert doc.duration_seconds > 0.0
    assert isinstance(doc.segments, list)
    assert isinstance(doc.all_words, list)
