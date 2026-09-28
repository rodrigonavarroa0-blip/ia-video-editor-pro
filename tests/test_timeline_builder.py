"""Tests unitarios para el constructor de Virtual Timeline (TimelineBuilder)."""

from app.models.editorial import EditAction, EditDecision, EditorialPlan
from app.models.vision import ReframeKeyframe
from app.timeline.builder import TimelineBuilder


def test_timeline_builder_continuity():
    d1 = EditDecision(action=EditAction.KEEP, source_in=0.0, source_out=2.0, reason="intro")
    d2 = EditDecision(action=EditAction.CUT, source_in=2.0, source_out=3.5, reason="silence")
    d3 = EditDecision(action=EditAction.ZOOM_IN, source_in=3.5, source_out=6.0, reason="punch-in")

    plan = EditorialPlan(
        project_id="test_proj",
        summary="Test Plan",
        hook_score=0.8,
        retention_score=0.85,
        redundancy_score=0.1,
        decisions=[d1, d2, d3],
        target_duration_seconds=4.5,
    )

    kf = ReframeKeyframe(timestamp=0.0, crop_x=0.34, crop_y=0.0, crop_width=0.3164, crop_height=1.0)

    timeline = TimelineBuilder.build_timeline(
        project_name="Continuity Test",
        raw_source_path="/path/to/raw.mp4",
        editorial_plan=plan,
        reframing_keyframes=[kf],
    )

    # 1. Debe haber 2 clips (el corte CUT se omite)
    assert len(timeline.video_clips) == 2

    # 2. El primer clip va de 0.0s a 2.0s
    c1 = timeline.video_clips[0]
    assert c1.timeline_in == 0.0
    assert c1.timeline_out == 2.0
    assert c1.scale == 1.0

    # 3. El segundo clip debe comenzar EXACTAMENTE en 2.0s (continuidad perfecta sin huecos)
    c2 = timeline.video_clips[1]
    assert c2.timeline_in == 2.0
    assert c2.timeline_out == 4.5
    assert c2.scale == 1.15  # ZOOM_IN

    # 4. Duración total
    assert timeline.duration_seconds == 4.5
