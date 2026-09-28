"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 8 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app
from app.models.editorial import EditAction, EditDecision, EditorialPlan
from app.timeline.builder import TimelineBuilder

runner = CliRunner()


def test_qa_zero_duration_clips_filtering():
    """Prueba que decisiones con duración 0.0 o negativas sean descartadas sin generar timecodes corruptos."""
    d1 = EditDecision(action=EditAction.KEEP, source_in=1.0, source_out=1.0, reason="zero dur")
    d2 = EditDecision(action=EditAction.KEEP, source_in=2.0, source_out=4.0, reason="valid")
    plan = EditorialPlan(
        project_id="qa_zero_proj",
        summary="Zero dur test",
        hook_score=0.5,
        retention_score=0.5,
        redundancy_score=0.0,
        decisions=[d1, d2],
        target_duration_seconds=2.0,
    )

    timeline = TimelineBuilder.build_timeline(
        project_name="Zero Dur QA",
        raw_source_path="/raw/vid.mp4",
        editorial_plan=plan,
    )

    assert len(timeline.video_clips) == 1
    assert timeline.video_clips[0].timeline_in == 0.0
    assert timeline.video_clips[0].timeline_out == 2.0


def test_qa_cli_build_timeline_command(synthetic_video: Path, tmp_path: Path):
    """Prueba el comando CLI iva build-timeline."""
    proj_dir = str(tmp_path / "cli_timeline_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])
    runner.invoke(app, ["plan-edit", proj_dir, "--offline"])

    res = runner.invoke(app, ["build-timeline", proj_dir, "--fps", "30", "--width", "1080", "--height", "1920"])
    assert res.exit_code == 0
    assert "Timeline Virtual e Integraciones NLE Generadas" in res.stdout
