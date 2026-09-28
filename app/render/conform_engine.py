"""Motor de conformación a RAW y generación de grafos de filtros FFmpeg (§37)."""

from pathlib import Path

from app.core.logger import render_logger
from app.models.timeline import VirtualTimeline
from app.subtitles.burner import SubtitleBurner


class ConformEngine:
    """Genera la cadena de filtros complejos de FFmpeg para aplicar cortes, zooms 9:16 y subtítulos a material RAW."""

    @classmethod
    def build_filter_complex(
        cls,
        timeline: VirtualTimeline,
        source_width: int,
        source_height: int,
        target_width: int = 1080,
        target_height: int = 1920,
        subtitle_file: Path | None = None,
    ) -> tuple[str, str]:
        """
        Construye el filter_complex de FFmpeg y retorna (filter_str, final_output_map).
        """
        if not timeline.video_clips:
            raise ValueError("El VirtualTimeline no contiene clips de video para renderizar.")

        render_logger.info(
            f"Construyendo filter_complex para {len(timeline.video_clips)} clips "
            f"({source_width}x{source_height} -> {target_width}x{target_height})"
        )

        filter_parts = []
        clip_labels = []

        # Determinar si el video fuente es horizontal o vertical
        is_source_horizontal = source_width >= source_height
        target_aspect = target_width / target_height  # 9/16 = 0.5625

        for idx, clip in enumerate(timeline.video_clips):
            v_label = f"v{idx}"
            clip_labels.append(f"[{v_label}]")

            scale_factor = max(1.0, float(clip.scale))

            if is_source_horizontal:
                # Recorte 9:16 sobre video horizontal
                crop_w = int((source_height * target_aspect) / scale_factor)
                crop_h = int(source_height / scale_factor)
            else:
                # Video ya vertical
                crop_w = int(source_width / scale_factor)
                crop_h = int(source_height / scale_factor)

            # Asegurar dimensiones pares para evitar errores en códecs H.264
            crop_w = crop_w - (crop_w % 2)
            crop_h = crop_h - (crop_h % 2)

            center_x = clip.crop.center_x
            center_y = clip.crop.center_y

            crop_x = int((center_x * source_width) - (crop_w / 2.0))
            crop_y = int((center_y * source_height) - (crop_h / 2.0))

            crop_x = max(0, min(source_width - crop_w, crop_x))
            crop_y = max(0, min(source_height - crop_h, crop_y))

            clip_filter = (
                f"[0:v]trim=start={clip.source_in:.3f}:end={clip.source_out:.3f},"
                f"setpts=PTS-STARTPTS,"
                f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
                f"scale={target_width}:{target_height}:flags=lanczos,"
                f"setsar=1[{v_label}];"
            )
            filter_parts.append(clip_filter)

        # Concat de todos los clips
        num_clips = len(timeline.video_clips)
        concat_input = "".join(clip_labels)
        filter_parts.append(f"{concat_input}concat=n={num_clips}:v=1:a=0[vconcat]")

        # Añadir subtítulos si están definidos
        if subtitle_file and Path(subtitle_file).exists():
            escaped_sub = SubtitleBurner.escape_filter_path(subtitle_file)
            if Path(subtitle_file).suffix.lower() == ".ass":
                filter_parts.append(f";[vconcat]ass='{escaped_sub}'[vout]")
            else:
                filter_parts.append(f";[vconcat]subtitles='{escaped_sub}'[vout]")
            final_map = "[vout]"
        else:
            final_map = "[vconcat]"

        full_filter_str = "".join(filter_parts)
        return full_filter_str, final_map
