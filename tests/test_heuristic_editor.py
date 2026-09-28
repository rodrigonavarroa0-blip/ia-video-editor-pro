"""Tests unitarios para el motor heurístico local de edición."""

from app.ai.heuristic_editor import (
    HeuristicEditor,
    calculate_hook_score,
    calculate_redundancy_score,
    calculate_retention_score,
)
from app.models.analysis import AnalysisResult
from app.models.editorial import EditAction, SilenceInterval, SilenceSeverity
from app.models.media import MediaInfo
from app.models.transcript import TranscriptDocument, WordTimestamp


def test_hook_score_calculation():
    # Transcript con pregunta gancho en los primeros 3 segundos
    words_hook = [
        WordTimestamp(word="¿Sabías", start=0.0, end=0.6),
        WordTimestamp(word="este", start=0.65, end=0.9),
        WordTimestamp(word="secreto", start=0.95, end=1.5),
        WordTimestamp(word="increíble?", start=1.55, end=2.4),
    ]
    doc_hook = TranscriptDocument(
        language="es", duration_seconds=2.5, text="¿Sabías este secreto increíble?",
        segments=[], all_words=words_hook, word_count=4
    )
    score_hook = calculate_hook_score(doc_hook)
    assert score_hook >= 0.75, "Un inicio con pregunta y palabras clave debe tener alto Hook Score"

    # Transcript plano sin gancho
    words_flat = [
        WordTimestamp(word="bueno", start=0.0, end=0.6, is_filler=True),
        WordTimestamp(word="hola", start=1.0, end=1.4),
    ]
    doc_flat = TranscriptDocument(
        language="es", duration_seconds=2.0, text="bueno hola",
        segments=[], all_words=words_flat, word_count=2
    )
    score_flat = calculate_hook_score(doc_flat)
    assert score_flat < 0.70


def test_redundancy_score_calculation():
    # Texto con muchas muletillas y repeticiones
    words_rep = [
        WordTimestamp(word="tipo", start=0.0, end=0.3, is_filler=True),
        WordTimestamp(word="cosa", start=0.4, end=0.7),
        WordTimestamp(word="cosa", start=0.8, end=1.1),
        WordTimestamp(word="o sea", start=1.2, end=1.5, is_filler=True),
    ]
    doc_rep = TranscriptDocument(
        language="es", duration_seconds=2.0, text="tipo cosa cosa o sea",
        segments=[], all_words=words_rep, word_count=4
    )
    assert calculate_redundancy_score(doc_rep) > 0.40


def test_retention_score_calculation():
    silences = [
        SilenceInterval(start=1.0, end=3.5, duration=2.5, severity=SilenceSeverity.CUT_AGGRESSIVE, db_level=-45.0)
    ]
    # Video de 5s con 2.5s de silencio muerto = baja retención
    retention = calculate_retention_score(None, silences, total_duration=5.0)
    assert retention <= 0.65


def test_heuristic_editor_generates_valid_plan():
    words = [
        WordTimestamp(word="Aprende", start=0.1, end=0.6),
        WordTimestamp(word="a", start=0.65, end=0.8),
        WordTimestamp(word="editar", start=0.85, end=1.3),
        WordTimestamp(word="videos", start=1.35, end=1.9),
    ]
    doc = TranscriptDocument(
        language="es", duration_seconds=4.0, text="Aprende a editar videos",
        segments=[], all_words=words, word_count=4
    )
    silences = [
        SilenceInterval(start=2.0, end=3.5, duration=1.5, severity=SilenceSeverity.CUT_AGGRESSIVE, db_level=-50.0)
    ]
    media = MediaInfo(
        file_path="/tmp/video.mp4", file_name="video.mp4", file_size_bytes=1000,
        format_name="mp4", duration_seconds=4.0, video_streams=[], audio_streams=[]
    )
    analysis = AnalysisResult(
        project_id="test_plan", source_media_path="/tmp/video.mp4",
        media_info=media, transcript=doc, silence_intervals=silences, scenes=[], is_complete=True
    )

    plan = HeuristicEditor.generate_plan(analysis, target_profile="social")
    assert plan.project_id == "test_plan"
    assert len(plan.decisions) >= 2
    assert any(d.action == EditAction.CUT for d in plan.decisions), "Debe haber una decisión de corte por el silencio"
    assert plan.target_duration_seconds < 4.0
