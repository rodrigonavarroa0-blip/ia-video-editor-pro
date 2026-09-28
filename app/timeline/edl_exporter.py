"""Exportador de listas de decisión de edición (CMX 3600 EDL) (§34)."""

from pathlib import Path

from app.core.logger import render_logger
from app.models.timeline import VirtualTimeline


class EDLExporter:
    """Exporta el VirtualTimeline al estándar CMX 3600 EDL para Premiere Pro, DaVinci Resolve y Avid."""

    @classmethod
    def to_smpte_timecode(cls, seconds: float, fps: float = 30.0) -> str:
        """Convierte segundos a timecode SMPTE estándar HH:MM:SS:FF (Non-Drop Frame)."""
        sec = max(0.0, float(seconds))
        total_frames = round(sec * fps)

        hours = int(total_frames // (3600 * fps))
        rem = total_frames % (3600 * fps)
        minutes = int(rem // (60 * fps))
        rem = rem % (60 * fps)
        secs = int(rem // fps)
        frames = int(rem % fps)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

    @classmethod
    def export_cmx3600(
        cls,
        timeline: VirtualTimeline,
        output_path: Path,
        tape_name: str = "AX",
    ) -> Path:
        """Genera un archivo .edl estándar CMX 3600."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"TITLE: {timeline.project_id}",
            "FCM: NON-DROP FRAME",
            "",
        ]

        fps = timeline.fps or 30.0

        for idx, clip in enumerate(timeline.video_clips, 1):
            src_in_tc = cls.to_smpte_timecode(clip.source_in, fps)
            src_out_tc = cls.to_smpte_timecode(clip.source_out, fps)
            tl_in_tc = cls.to_smpte_timecode(clip.timeline_in, fps)
            tl_out_tc = cls.to_smpte_timecode(clip.timeline_out, fps)

            # Formato estándar CMX: 001  AX       V     C        00:00:00:00 00:00:02:15 00:00:00:00 00:00:02:15
            event_line = f"{idx:03d}  {tape_name:<8} V     C        {src_in_tc} {src_out_tc} {tl_in_tc} {tl_out_tc}"
            lines.append(event_line)

            source_name = Path(clip.source_path).name
            lines.append(f"* FROM CLIP NAME: {source_name}")
            if clip.scale != 1.0:
                lines.append(f"* SCALE: {clip.scale:.2f}")
            lines.append("")

        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        render_logger.info(f"EDL CMX 3600 exportado con éxito: {out.name} ({len(timeline.video_clips)} eventos)")
        return out
