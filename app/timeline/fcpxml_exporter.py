"""Exportador de proyectos a formato FCPXML para Final Cut Pro y DaVinci Resolve (§35)."""

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from app.core.logger import render_logger
from app.models.timeline import VirtualTimeline


class FCPXMLExporter:
    """Genera documentos XML en formato FCPXML v1.9 para Final Cut Pro X y DaVinci Resolve."""

    @classmethod
    def export_fcpxml(cls, timeline: VirtualTimeline, output_path: Path) -> Path:
        """Exporta el timeline virtual a un archivo .fcpxml válido y bien estructurado."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        fps = int(timeline.fps or 30)
        total_duration_sec = timeline.duration_seconds
        total_dur_str = f"{round(total_duration_sec * fps)}/{fps}s"

        # 1. Raíz <fcpxml>
        root = ET.Element("fcpxml", {"version": "1.9"})

        # 2. <resources>
        resources = ET.SubElement(root, "resources")
        fmt_id = "r1"
        ET.SubElement(
            resources,
            "format",
            {
                "id": fmt_id,
                "name": f"FFVideoFormat{timeline.width}x{timeline.height}p{fps}",
                "frameDuration": f"1/{fps}s",
                "width": str(timeline.width),
                "height": str(timeline.height),
            },
        )

        # Mapear assets de video fuente únicos
        asset_map = {}
        for idx, clip in enumerate(timeline.video_clips, 2):
            src_path = clip.source_path
            if src_path not in asset_map:
                asset_id = f"r{idx}"
                asset_map[src_path] = asset_id
                src_url = Path(src_path).as_uri() if Path(src_path).is_absolute() else src_path
                ET.SubElement(
                    resources,
                    "asset",
                    {
                        "id": asset_id,
                        "name": Path(src_path).name,
                        "src": src_url,
                        "hasVideo": "1",
                        "hasAudio": "1",
                        "format": fmt_id,
                    },
                )

        # 3. <library> -> <event> -> <project> -> <sequence> -> <spine>
        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", {"name": f"{timeline.project_id} Event"})
        project = ET.SubElement(event, "project", {"name": timeline.project_id})
        sequence = ET.SubElement(
            project,
            "sequence",
            {
                "format": fmt_id,
                "duration": total_dur_str,
                "tcStart": "0/1s",
            },
        )
        spine = ET.SubElement(sequence, "spine")

        # 4. Insertar clips en el <spine>
        for clip in timeline.video_clips:
            asset_id = asset_map.get(clip.source_path, "r2")
            clip_dur_frames = round((clip.source_out - clip.source_in) * fps)
            clip_start_frames = round(clip.source_in * fps)
            clip_offset_frames = round(clip.timeline_in * fps)

            dur_str = f"{clip_dur_frames}/{fps}s"
            start_str = f"{clip_start_frames}/{fps}s"
            offset_str = f"{clip_offset_frames}/{fps}s"

            ET.SubElement(
                spine,
                "asset-clip",
                {
                    "ref": asset_id,
                    "name": clip.id,
                    "offset": offset_str,
                    "duration": dur_str,
                    "start": start_str,
                },
            )

        # Formatear e indentar XML
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")

        with open(out, "wb") as f:
            f.write(pretty_xml)

        render_logger.info(f"FCPXML exportado exitosamente: {out.name} ({len(timeline.video_clips)} clips)")
        return out
