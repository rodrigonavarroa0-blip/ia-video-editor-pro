"""Tests unitarios para el exportador OpenTimelineIO (OTIOExporter)."""

import json
from pathlib import Path

from app.models.timeline import VideoClipItem, VirtualTimeline
from app.timeline.otio_exporter import OTIOExporter


def test_export_otio_validity(tmp_path: Path):
    c1 = VideoClipItem(
        id="v1",
        source_path="/raw/test_otio.mp4",
        source_in=0.0,
        source_out=4.0,
        timeline_in=0.0,
        timeline_out=4.0,
    )
    timeline = VirtualTimeline(
        version=1,
        project_id="OTIO_TEST",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=4.0,
        video_clips=[c1],
    )

    out_otio = tmp_path / "test.otio"
    OTIOExporter.export_otio(timeline, out_otio)

    assert out_otio.exists()

    with open(out_otio, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["OTIO_SCHEMA"] == "Timeline.1"
    assert data["name"] == "OTIO_TEST"
    assert data["tracks"]["OTIO_SCHEMA"] == "Stack.1"
    assert len(data["tracks"]["children"]) >= 1
    assert data["tracks"]["children"][0]["children"][0]["OTIO_SCHEMA"] == "Clip.1"
