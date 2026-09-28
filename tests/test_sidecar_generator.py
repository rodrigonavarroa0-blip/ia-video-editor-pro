"""Tests unitarios para los exportadores sidecar SRT y WebVTT (SidecarGenerator)."""

from pathlib import Path

from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.subtitles.sidecar_generator import SidecarGenerator


def test_sidecar_timestamps():
    assert SidecarGenerator.format_srt_timestamp(1.456) == "00:00:01,456"
    assert SidecarGenerator.format_vtt_timestamp(1.456) == "00:00:01.456"


def test_generate_srt_and_vtt(tmp_path: Path):
    w1 = WordTimestamp(word="Bienvenidos", start=0.0, end=0.8)
    w2 = WordTimestamp(word="al", start=0.8, end=1.0)
    w3 = WordTimestamp(word="futuro", start=1.0, end=1.8)
    seg = TranscriptSegment(id=1, text="Bienvenidos al futuro", start=0.0, end=1.8, words=[w1, w2, w3])
    doc = TranscriptDocument(duration_seconds=1.8, text="Bienvenidos al futuro", segments=[seg], all_words=[w1, w2, w3], word_count=3)

    srt_out = tmp_path / "test.srt"
    vtt_out = tmp_path / "test.vtt"

    SidecarGenerator.generate_srt(doc, srt_out)
    SidecarGenerator.generate_vtt(doc, vtt_out)

    assert srt_out.exists()
    assert vtt_out.exists()

    srt_content = srt_out.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,800" in srt_content
    assert "Bienvenidos al futuro" in srt_content

    vtt_content = vtt_out.read_text(encoding="utf-8")
    assert vtt_content.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.800" in vtt_content
