"""Tests unitarios para el motor de conformación a RAW (ConformEngine)."""

from app.models.timeline import VideoClipItem, VirtualTimeline
from app.render.conform_engine import ConformEngine


def test_build_filter_complex_horizontal_to_vertical():
    c1 = VideoClipItem(
        id="v1",
        source_path="/path/to/raw.mp4",
        source_in=0.0,
        source_out=2.0,
        timeline_in=0.0,
        timeline_out=2.0,
        scale=1.0,
    )
    c2 = VideoClipItem(
        id="v2",
        source_path="/path/to/raw.mp4",
        source_in=3.0,
        source_out=5.0,
        timeline_in=2.0,
        timeline_out=4.0,
        scale=1.15,  # ZOOM_IN
    )
    timeline = VirtualTimeline(
        version=1,
        project_id="FilterTest",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=4.0,
        video_clips=[c1, c2],
    )

    filter_str, out_map = ConformEngine.build_filter_complex(
        timeline=timeline,
        source_width=1920,
        source_height=1080,
        target_width=1080,
        target_height=1920,
    )

    assert "trim=start=0.000:end=2.000" in filter_str
    assert "trim=start=3.000:end=5.000" in filter_str
    assert "scale=1080:1920" in filter_str
    assert "concat=n=2:v=1:a=0[vconcat]" in filter_str
    assert out_map == "[vconcat]"
