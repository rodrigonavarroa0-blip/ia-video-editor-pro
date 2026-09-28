"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 2 (§107)."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from app.ai.speech_transcriber import (
    DEFAULT_FILLER_WORDS,
    SpeechTranscriber,
    clean_word_text,
)
from app.cli.main import app
from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.utils.ffmpeg import FFmpegManager

runner = CliRunner()


def test_qa_silent_audio_transcription(tmp_path: Path):
    """Prueba con audio con silencio digital absoluto (0dB) sin habla humana."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    silent_wav = tmp_path / "absolute_silence.wav"
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "2",
        "-acodec", "pcm_s16le",
        str(silent_wav),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    doc = SpeechTranscriber.transcribe(silent_wav, model_size="tiny", language="es")
    assert doc is not None
    assert doc.word_count == 0
    assert len(doc.segments) == 0


def test_qa_timestamp_monotonicity():
    """Valida que todos los timestamps cumplan estrictamente start <= end y no sean negativos."""
    words = [
        WordTimestamp(word="Hola", start=0.0, end=0.4),
        WordTimestamp(word="a", start=0.45, end=0.6),
        WordTimestamp(word="todos", start=0.65, end=1.1),
    ]
    seg = TranscriptSegment(id=1, text="Hola a todos", start=0.0, end=1.1, words=words)
    doc = TranscriptDocument(language="es", duration_seconds=1.1, text="Hola a todos", segments=[seg], all_words=words, word_count=3)

    for w in doc.all_words:
        assert w.start >= 0.0
        assert w.start <= w.end
        assert w.end <= doc.duration_seconds + 0.1


def test_qa_filler_word_tagging():
    """Prueba el etiquetado léxico de muletillas."""
    fillers = DEFAULT_FILLER_WORDS["es"]
    sample_text = ["Hola", "eh", "este", "vamos", "a", "ver", "o sea", "básicamente"]
    tagged = []
    for word in sample_text:
        clean = clean_word_text(word)
        is_filler = clean in fillers
        tagged.append((word, is_filler))

    assert dict(tagged)["eh"] is True
    assert dict(tagged)["este"] is True
    assert dict(tagged)["básicamente"] is True
    assert dict(tagged)["vamos"] is False
    assert dict(tagged)["Hola"] is False


def test_qa_cli_transcribe_command(synthetic_video: Path, tmp_path: Path):
    """Prueba la ejecución completa del comando CLI iva transcribe."""
    proj_dir = str(tmp_path / "cli_transcribe_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])

    result = runner.invoke(app, ["transcribe", proj_dir, "--model", "tiny"])
    assert result.exit_code == 0
    assert "Transcripción guardada en" in result.stdout
