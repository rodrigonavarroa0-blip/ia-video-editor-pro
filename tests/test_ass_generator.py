"""Tests unitarios para el generador de subtítulos cinéticos ASS (ASSGenerator)."""

from pathlib import Path

from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.subtitles.ass_generator import ASSGenerator


def test_ass_timestamp_formatting():
    assert ASSGenerator.format_timestamp(0.0) == "0:00:00.00"
    assert ASSGenerator.format_timestamp(1.45) == "0:00:01.45"
    assert ASSGenerator.format_timestamp(65.12) == "0:01:05.12"
    assert ASSGenerator.format_timestamp(3661.05) == "1:01:01.05"


def test_generate_ass_script_structure(tmp_path: Path):
    w1 = WordTimestamp(word="Hola", start=0.0, end=0.5)
    w2 = WordTimestamp(word="mundo", start=0.5, end=1.0)
    w3 = WordTimestamp(word="cinemático", start=1.0, end=2.0)
    seg = TranscriptSegment(id=1, text="Hola mundo cinemático", start=0.0, end=2.0, words=[w1, w2, w3])
    doc = TranscriptDocument(duration_seconds=2.0, text="Hola mundo cinemático", segments=[seg], all_words=[w1, w2, w3], word_count=3)

    out_ass = tmp_path / "test.ass"
    cfg = ASSGenerator.get_style_config("hormozi")
    ASSGenerator.generate_ass(doc, out_ass, style_config=cfg)

    assert out_ass.exists()
    content = out_ass.read_text(encoding="utf-8")

    # 1. Verificar cabeceras estándar ASS v4.00+
    assert "[Script Info]" in content
    assert "ScriptType: v4.00+" in content
    assert "[V4+ Styles]" in content
    assert "Style: Default" in content
    assert "[Events]" in content

    # 2. Verificar eventos de diálogo con palabra activa
    assert "Dialogue: 0," in content
    assert r"{\c&H0000FFFF&" in content  # Color activo amarillo oro en estilo Hormozi
