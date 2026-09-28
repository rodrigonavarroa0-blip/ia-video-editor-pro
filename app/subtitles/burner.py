"""Quemador de subtítulos en video mediante FFmpeg y libass (§32)."""

import subprocess
from pathlib import Path

from app.core.logger import render_logger
from app.utils.ffmpeg import FFmpegManager


class SubtitleBurner:
    """Quema subtítulos cinéticos (.ass) o estándar (.srt) directamente en los fotogramas de video."""

    @classmethod
    def escape_filter_path(cls, path: Path) -> str:
        """
        Escapa caracteres especiales (dos puntos ':', barras invertidas '\' y espacios)
        para usarse de forma segura dentro de argumentos de filtros complejos de FFmpeg.
        """
        raw_str = str(Path(path).resolve())
        # En sistemas Unix/macOS, los dos puntos dentro de filtros FFmpeg dividen parámetros
        return raw_str.replace("\\", "/").replace(":", "\\:")

    @classmethod
    def burn_subtitles(
        cls,
        input_video: Path,
        subtitle_file: Path,
        output_video: Path,
        encoder: str | None = None,
    ) -> Path:
        """
        Quema el archivo de subtítulos (.ass o .srt) en el video usando FFmpeg libass.
        """
        in_vid = Path(input_video).resolve()
        sub_path = Path(subtitle_file).resolve()
        out_vid = Path(output_video).resolve()
        out_vid.parent.mkdir(parents=True, exist_ok=True)

        if not in_vid.exists():
            raise FileNotFoundError(f"Video de entrada no encontrado: {in_vid}")
        if not sub_path.exists():
            raise FileNotFoundError(f"Archivo de subtítulos no encontrado: {sub_path}")

        ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
        selected_encoder = encoder or FFmpegManager.get_optimal_video_encoder()

        render_logger.info(f"Quemando subtítulos {sub_path.suffix} en: {out_vid.name} (Encoder: {selected_encoder})")

        escaped_sub = cls.escape_filter_path(sub_path)
        if sub_path.suffix.lower() == ".ass":
            vf_filter = f"ass='{escaped_sub}'"
        else:
            vf_filter = f"subtitles='{escaped_sub}'"

        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(in_vid),
            "-vf", vf_filter,
            "-c:v", selected_encoder,
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(out_vid),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode("utf-8", errors="replace")
            # Si el encoder hardware falló (p.ej. VideoToolbox), reintentar con CPU libx264
            if selected_encoder != "libx264":
                render_logger.warning(f"Fallo con {selected_encoder}, reintentando con libx264...")
                cmd[cmd.index("-c:v") + 1] = "libx264"
                subprocess.run(cmd, capture_output=True, check=True)
            else:
                render_logger.error(f"Error en FFmpeg quemando subtítulos: {err_msg}")
                raise RuntimeError(f"Fallo al quemar subtítulos con FFmpeg: {err_msg}")

        render_logger.info(f"Quemado de subtítulos completado: {out_vid.name}")
        return out_vid
