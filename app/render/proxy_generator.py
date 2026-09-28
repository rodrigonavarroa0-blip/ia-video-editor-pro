"""Generador de proxies ligeros y extractor de audio WAV para IA Video Editor Pro."""

from collections.abc import Callable
from pathlib import Path

from app.core.logger import render_logger
from app.models.media import MediaInfo
from app.utils.ffmpeg import FFmpegManager


class ProxyGenerator:
    """Genera proxies optimizados para análisis y previsualización, y extrae audio PCM."""

    @classmethod
    def generate_proxy(
        cls,
        source_path: Path,
        output_path: Path,
        media_info: MediaInfo | None = None,
        max_dimension: int = 1280,
        crf: int = 28,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """
        Genera un proxy liviano H.264 manteniendo la relación de aspecto original
        y escalando la dimensión máxima a max_dimension (ej. 720p).
        """
        source = Path(source_path).resolve()
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        duration = media_info.duration_seconds if media_info else None
        has_audio = media_info.has_audio if media_info is not None else True

        # Filtro de escalado proporcional determinista asegurando dimensiones pares (divisibles por 2)
        scale_filter = f"scale='if(gt(iw,ih),min({max_dimension},iw),-2)':'if(gt(iw,ih),-2,min({max_dimension},ih))'"

        encoder = FFmpegManager.get_optimal_video_encoder()

        # Argumentos de codificación
        args = [
            "-y",
            "-i", str(source),
            "-vf", scale_filter,
            "-c:v", encoder,
        ]

        if encoder == "libx264":
            args.extend(["-preset", "veryfast", "-crf", str(crf)])
        elif encoder == "h264_videotoolbox":
            args.extend(["-b:v", "2500k"])

        if has_audio:
            args.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
                "-ar", "44100",
            ])
        else:
            args.append("-an")

        args.extend([
            "-pix_fmt", "yuv420p",
            str(output),
        ])

        render_logger.info(f"Generando proxy 720p: {source.name} -> {output.name} (has_audio={has_audio})")
        FFmpegManager.run_command(args, duration_seconds=duration, progress_callback=progress_callback)
        return output

    @classmethod
    def extract_audio_wav(
        cls,
        source_path: Path,
        output_wav_path: Path,
        sample_rate: int = 44100,
        channels: int = 1,
        duration_seconds: float | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """
        Extrae el audio del video en formato WAV PCM de 16-bit normalizado
        para inferencia en Whisper y análisis espectral/DSP.
        """
        source = Path(source_path).resolve()
        output = Path(output_wav_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "-y",
            "-i", str(source),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            str(output),
        ]

        render_logger.info(f"Extrayendo audio WAV ({sample_rate}Hz, {channels}ch): {source.name} -> {output.name}")
        FFmpegManager.run_command(args, duration_seconds=duration_seconds, progress_callback=progress_callback)
        return output
