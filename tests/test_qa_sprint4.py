"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 4 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.ai.heuristic_editor import HeuristicEditor
from app.cli.main import app
from app.models.analysis import AnalysisResult
from app.models.editorial import EditAction
from app.models.media import MediaInfo
from app.models.transcript import TranscriptDocument

runner = CliRunner()


def test_qa_editorial_zero_speech_video():
    """Prueba la generación de plan editorial cuando el video no contiene habla humana."""
    media = MediaInfo(
        file_path="/tmp/silent_video.mp4", file_name="silent_video.mp4", file_size_bytes=5000,
        format_name="mp4", duration_seconds=5.0, video_streams=[], audio_streams=[]
    )
    doc_empty = TranscriptDocument(
        language="es", duration_seconds=5.0, text="", segments=[], all_words=[], word_count=0
    )
    analysis = AnalysisResult(
        project_id="zero_speech", source_media_path="/tmp/silent_video.mp4",
        media_info=media, transcript=doc_empty, silence_intervals=[], scenes=[], is_complete=True
    )

    plan = HeuristicEditor.generate_plan(analysis, target_profile="social")
    assert plan is not None
    assert plan.target_duration_seconds > 0.0
    assert len(plan.decisions) >= 1


def test_qa_decision_interval_consistency():
    """Valida la consistencia temporal estricta de cada EditDecision."""
    media = MediaInfo(
        file_path="/tmp/vid.mp4", file_name="vid.mp4", file_size_bytes=1000,
        format_name="mp4", duration_seconds=10.0, video_streams=[], audio_streams=[]
    )
    analysis = AnalysisResult(
        project_id="consistency_test", source_media_path="/tmp/vid.mp4",
        media_info=media, transcript=None, silence_intervals=[], scenes=[], is_complete=True
    )

    plan = HeuristicEditor.generate_plan(analysis, target_profile="social")
    for d in plan.decisions:
        assert d.source_in >= 0.0
        assert d.source_in <= d.source_out
        if d.action == EditAction.CUT:
            assert d.target_duration == 0.0
        else:
            assert d.target_duration > 0.0


def test_qa_long_speech_zoom_punchin():
    """Comprueba que un segmento largo de habla (> 4.5s) genere un ZOOM_IN para dinamismo."""
    media = MediaInfo(
        file_path="/tmp/long.mp4", file_name="long.mp4", file_size_bytes=1000,
        format_name="mp4", duration_seconds=8.0, video_streams=[], audio_streams=[]
    )
    analysis = AnalysisResult(
        project_id="zoom_test", source_media_path="/tmp/long.mp4",
        media_info=media, transcript=None, silence_intervals=[], scenes=[], is_complete=True
    )

    plan = HeuristicEditor.generate_plan(analysis, target_profile="social")
    # Para 8 segundos continuos debe existir una decisión de corte ZOOM_IN
    has_zoom = any(d.action == EditAction.ZOOM_IN for d in plan.decisions)
    assert has_zoom is True


def test_qa_cli_plan_edit_command(synthetic_video: Path, tmp_path: Path):
    """Prueba la ejecución en CLI del comando iva plan-edit."""
    proj_dir = str(tmp_path / "cli_plan_edit_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])
    runner.invoke(app, ["analyze", proj_dir])

    result = runner.invoke(app, ["plan-edit", proj_dir, "--offline"])
    assert result.exit_code == 0
    assert "Plan Editorial Generado Exitosamente" in result.stdout
    assert "Decisiones de Edición" in result.stdout
