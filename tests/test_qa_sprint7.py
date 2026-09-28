"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 7 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app
from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.subtitles.ass_generator import ASSGenerator
from app.subtitles.burner import SubtitleBurner

runner = CliRunner()


def test_qa_special_characters_in_subtitles(tmp_path: Path):
    """Prueba que caracteres hostiles (llaves, comillas, barras invertidas) sean escapados correctamente."""
    hostile_words = [
        WordTimestamp(word="{test}", start=0.0, end=0.5),
        WordTimestamp(word="path\\to\\file", start=0.5, end=1.0),
        WordTimestamp(word="\"comillas\"", start=1.0, end=1.5),
        WordTimestamp(word="¡Atención!", start=1.5, end=2.0),
    ]
    seg = TranscriptSegment(id=1, text="{test} path\\to\\file \"comillas\" ¡Atención!", start=0.0, end=2.0, words=hostile_words)
    doc = TranscriptDocument(duration_seconds=2.0, text=seg.text, segments=[seg], all_words=hostile_words, word_count=4)

    out_ass = tmp_path / "hostile.ass"
    ASSGenerator.generate_ass(doc, out_ass)

    assert out_ass.exists()
    content = out_ass.read_text(encoding="utf-8")
    # No deben quedar llaves sin balancear en el texto
    assert "Dialogue:" in content


def test_qa_empty_transcript_handling(tmp_path: Path):
    """Prueba que una transcripción sin palabras genere archivos válidos sin crash."""
    doc = TranscriptDocument(duration_seconds=0.0, text="", segments=[], all_words=[], word_count=0)
    out_ass = tmp_path / "empty.ass"
    ASSGenerator.generate_ass(doc, out_ass)
    assert out_ass.exists()
    assert "[Script Info]" in out_ass.read_text(encoding="utf-8")


def test_qa_video_subtitle_burning(synthetic_video: Path, tmp_path: Path):
    """Prueba el quemado real con FFmpeg libass sobre un archivo de video."""
    words = [
        WordTimestamp(word="QUEMADO", start=0.0, end=0.8),
        WordTimestamp(word="DE", start=0.8, end=1.2),
        WordTimestamp(word="SUBTITULOS", start=1.2, end=2.0),
    ]
    seg = TranscriptSegment(id=1, text="QUEMADO DE SUBTITULOS", start=0.0, end=2.0, words=words)
    doc = TranscriptDocument(duration_seconds=2.0, text=seg.text, segments=[seg], all_words=words, word_count=3)

    ass_path = tmp_path / "burned_test.ass"
    ASSGenerator.generate_ass(doc, ass_path)

    out_video = tmp_path / "burned_output.mp4"
    SubtitleBurner.burn_subtitles(
        input_video=synthetic_video,
        subtitle_file=ass_path,
        output_video=out_video,
    )

    assert out_video.exists()
    assert out_video.stat().st_size > 1000


def test_qa_cli_subtitles_commands(synthetic_video: Path, tmp_path: Path):
    """Prueba los comandos CLI generate-subtitles y burn-subtitles."""
    proj_dir = str(tmp_path / "cli_subs_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])
    runner.invoke(app, ["transcribe", proj_dir, "--model", "tiny"])

    # 1. iva generate-subtitles
    res_gen = runner.invoke(app, ["generate-subtitles", proj_dir, "--style", "hormozi"])
    assert res_gen.exit_code == 0
    assert "Subtítulos Cinéticos Generados Exitosamente" in res_gen.stdout

    # 2. iva burn-subtitles
    res_burn = runner.invoke(app, ["burn-subtitles", proj_dir, "--style", "hormozi"])
    assert res_burn.exit_code == 0
    assert "Previsualización Subtitulada Generada" in res_burn.stdout
