"""Tests unitarios para el exportador FCPXML (FCPXMLExporter)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from app.models.timeline import VideoClipItem, VirtualTimeline
from app.timeline.fcpxml_exporter import FCPXMLExporter


def test_export_fcpxml_validity(tmp_path: Path):
    c1 = VideoClipItem(
        id="v1",
        source_path="/raw/test_video.mp4",
        source_in=0.0,
        source_out=3.0,
        timeline_in=0.0,
        timeline_out=3.0,
    )
    timeline = VirtualTimeline(
        version=1,
        project_id="FCPXML_TEST",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=3.0,
        video_clips=[c1],
    )

    out_fcpxml = tmp_path / "test.fcpxml"
    FCPXMLExporter.export_fcpxml(timeline, out_fcpxml)

    assert out_fcpxml.exists()

    # Validar que el XML sea sintácticamente perfecto
    tree = ET.parse(out_fcpxml)
    root = tree.getroot()

    assert root.tag == "fcpxml"
    assert root.attrib["version"] == "1.9"

    resources = root.find("resources")
    assert resources is not None
    assert len(resources.findall("format")) >= 1
    assert len(resources.findall("asset")) >= 1

    spine = root.find(".//spine")
    assert spine is not None
    assert len(spine.findall("asset-clip")) == 1
