"""Tests unitarios para el exportador CMX 3600 EDL (EDLExporter)."""

from pathlib import Path

from app.models.timeline import VideoClipItem, VirtualTimeline
from app.timeline.edl_exporter import EDLExporter


def test_smpte_timecode_conversions():
    assert EDLExporter.to_smpte_timecode(0.0, fps=30.0) == "00:00:00:00"
    assert EDLExporter.to_smpte_timecode(1.0, fps=30.0) == "00:00:01:00"
    assert EDLExporter.to_smpte_timecode(1.5, fps=30.0) == "00:00:01:15"
    assert EDLExporter.to_smpte_timecode(65.0, fps=30.0) == "00:01:05:00"


def test_export_cmx3600_structure(tmp_path: Path):
    c1 = VideoClipItem(
        id="v1",
        source_path="/raw/clip1.mp4",
        source_in=0.0,
        source_out=2.5,
        timeline_in=0.0,
        timeline_out=2.5,
    )
    c2 = VideoClipItem(
        id="v2",
        source_path="/raw/clip1.mp4",
        source_in=5.0,
        source_out=8.0,
        timeline_in=2.5,
        timeline_out=5.5,
        scale=1.15,
    )
    timeline = VirtualTimeline(
        version=1,
        project_id="EDL_TEST",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=5.5,
        video_clips=[c1, c2],
    )

    out_edl = tmp_path / "test.edl"
    EDLExporter.export_cmx3600(timeline, out_edl)

    assert out_edl.exists()
    content = out_edl.read_text(encoding="utf-8")

    assert "TITLE: EDL_TEST" in content
    assert "FCM: NON-DROP FRAME" in content
    assert "001  AX       V     C        00:00:00:00 00:00:02:15 00:00:00:00 00:00:02:15" in content
    assert "002  AX       V     C        00:00:05:00 00:00:08:00 00:00:02:15 00:00:05:15" in content
    assert "* FROM CLIP NAME: clip1.mp4" in content
