"""Tests unitarios para el motor de renderizado final (RenderEngine)."""

from pathlib import Path

from app.models.timeline import VideoClipItem, VirtualTimeline
from app.render.render_engine import RenderEngine


def test_render_timeline_synthetic(synthetic_video: Path, tmp_path: Path):
    c1 = VideoClipItem(
        id="v1",
        source_path=str(synthetic_video),
        source_in=0.0,
        source_out=1.5,
        timeline_in=0.0,
        timeline_out=1.5,
    )
    timeline = VirtualTimeline(
        version=1,
        project_id="RenderTest",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=1.5,
        video_clips=[c1],
    )

    out_file = tmp_path / "final_test.mp4"
    meta = RenderEngine.render_timeline(
        timeline=timeline,
        raw_source_path=synthetic_video,
        output_file=out_file,
        preset_name="preview",
    )

    assert out_file.exists()
    assert out_file.stat().st_size > 1000
    assert meta["width"] == 720
    assert meta["height"] == 1280
    assert meta["duration_seconds"] > 1.0
    assert "sha256" in meta
