"""Exportador de proyectos al estándar abierto OpenTimelineIO (.otio) (§36)."""

import json
from pathlib import Path

from app.core.logger import render_logger
from app.models.timeline import VirtualTimeline


class OTIOExporter:
    """Genera la estructura de intercambio estándar de la Academy Software Foundation / Pixar (.otio)."""

    @classmethod
    def export_otio(cls, timeline: VirtualTimeline, output_path: Path) -> Path:
        """Exporta el timeline virtual a un archivo JSON compatible con OpenTimelineIO."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        fps = float(timeline.fps or 30.0)

        # Construir clips de video
        video_children = []
        for clip in timeline.video_clips:
            start_frame = round(clip.source_in * fps)
            dur_frames = round((clip.source_out - clip.source_in) * fps)

            video_children.append({
                "OTIO_SCHEMA": "Clip.1",
                "name": clip.id,
                "source_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": fps,
                        "value": start_frame,
                    },
                    "duration": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": fps,
                        "value": dur_frames,
                    },
                },
                "media_reference": {
                    "OTIO_SCHEMA": "ExternalReference.1",
                    "target_url": clip.source_path,
                },
                "metadata": {
                    "scale": clip.scale,
                    "crop_center_x": clip.crop.center_x,
                    "crop_center_y": clip.crop.center_y,
                },
            })

        # Construir clips de audio
        audio_children = []
        for clip in timeline.audio_clips:
            start_frame = round(clip.source_in * fps)
            dur_frames = round((clip.source_out - clip.source_in) * fps)

            audio_children.append({
                "OTIO_SCHEMA": "Clip.1",
                "name": clip.id,
                "source_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": fps,
                        "value": start_frame,
                    },
                    "duration": {
                        "OTIO_SCHEMA": "RationalTime.1",
                        "rate": fps,
                        "value": dur_frames,
                    },
                },
                "media_reference": {
                    "OTIO_SCHEMA": "ExternalReference.1",
                    "target_url": clip.source_path,
                },
            })

        otio_doc = {
            "OTIO_SCHEMA": "Timeline.1",
            "name": timeline.project_id,
            "global_start_time": {
                "OTIO_SCHEMA": "RationalTime.1",
                "rate": fps,
                "value": 0,
            },
            "tracks": {
                "OTIO_SCHEMA": "Stack.1",
                "name": "tracks",
                "children": [
                    {
                        "OTIO_SCHEMA": "Track.1",
                        "name": "Video Track 1",
                        "kind": "Video",
                        "children": video_children,
                    },
                    {
                        "OTIO_SCHEMA": "Track.1",
                        "name": "Audio Track 1",
                        "kind": "Audio",
                        "children": audio_children,
                    },
                ],
            },
        }

        with open(out, "w", encoding="utf-8") as f:
            json.dump(otio_doc, f, indent=2, ensure_ascii=False)

        render_logger.info(f"OpenTimelineIO (.otio) exportado exitosamente: {out.name}")
        return out
