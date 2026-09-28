"""Analizador de metadatos e inspección técnica de medios audiovisuales."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from app.core.logger import analysis_logger
from app.models.media import AudioStreamInfo, MediaInfo, VideoStreamInfo
from app.utils.ffmpeg import FFmpegManager


def _parse_fps(fps_str: str | None) -> float:
    """Convierte una cadena de tasa de fotogramas fraccionaria (ej. '30000/1001' o '30/1') a float."""
    if not fps_str or fps_str == "0/0":
        return 30.0
    if "/" in fps_str:
        try:
            num, den = fps_str.split("/")
            return float(num) / float(den) if float(den) != 0 else 30.0
        except Exception:
            return 30.0
    try:
        return float(fps_str)
    except Exception:
        return 30.0


def _calculate_aspect_ratio(width: int, height: int) -> str:
    """Calcula la relación de aspecto estándar más cercana."""
    if height == 0:
        return "16:9"
    ratio = width / height
    if abs(ratio - (16 / 9)) < 0.05:
        return "16:9"
    if abs(ratio - (9 / 16)) < 0.05:
        return "9:16"
    if abs(ratio - (4 / 3)) < 0.05:
        return "4:3"
    if abs(ratio - (1 / 1)) < 0.05:
        return "1:1"
    if abs(ratio - (21 / 9)) < 0.05:
        return "21:9"
    return f"{width}:{height}"


class MediaProbe:
    """Inspecciona y extrae metadatos técnicos completos de un archivo multimedia."""

    @classmethod
    def probe(cls, file_path: Path) -> MediaInfo:
        """Ejecuta inspección técnica y retorna un modelo MediaInfo validado."""
        media_path = Path(file_path).resolve()
        if not media_path.exists():
            raise FileNotFoundError(f"Archivo multimedia no encontrado: {media_path}")

        file_size_bytes = media_path.stat().st_size
        if file_size_bytes == 0:
            raise ValueError(f"El archivo está vacío (0 bytes): {media_path}")

        ffprobe_exe = FFmpegManager.get_ffprobe_path()

        # Si ffprobe está instalado y disponible, usar modo JSON
        if ffprobe_exe:
            cmd = [
                ffprobe_exe,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(media_path),
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    return cls._parse_ffprobe_json(media_path, file_size_bytes, data)
                elif "Invalid data found" in result.stderr:
                    raise ValueError(f"Archivo multimedia corrupto o formato no soportado: {media_path.name}")
            except ValueError:
                raise
            except Exception as e:
                analysis_logger.warning(f"Error procesando ffprobe JSON: {e}, recurriendo a probe directo.")

        # Fallback ultra-robusto usando ffmpeg -i
        return cls._fallback_probe(media_path, file_size_bytes)

    @classmethod
    def _parse_ffprobe_json(cls, media_path: Path, file_size_bytes: int, data: dict[str, Any]) -> MediaInfo:
        """Parsea la salida JSON estándar de ffprobe."""
        format_data = data.get("format", {})
        streams_data = data.get("streams", [])

        format_name = format_data.get("format_name", "unknown")
        duration_seconds = float(format_data.get("duration", 0.0))

        video_streams: list[VideoStreamInfo] = []
        audio_streams: list[AudioStreamInfo] = []

        for stream in streams_data:
            codec_type = stream.get("codec_type")
            if codec_type == "video":
                disposition = stream.get("disposition", {})
                if disposition.get("attached_pic") == 1:
                    continue

                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                if width > 0 and height > 0:
                    fps = _parse_fps(stream.get("r_frame_rate") or stream.get("avg_frame_rate"))
                    stream_dur = float(stream.get("duration", duration_seconds))
                    if duration_seconds == 0.0:
                        duration_seconds = stream_dur

                    video_streams.append(
                        VideoStreamInfo(
                            index=int(stream.get("index", 0)),
                            codec_name=stream.get("codec_name", "unknown"),
                            width=width,
                            height=height,
                            aspect_ratio=_calculate_aspect_ratio(width, height),
                            fps=fps,
                            duration_seconds=stream_dur,
                            pixel_format=stream.get("pix_fmt"),
                            color_space=stream.get("color_space"),
                        )
                    )
            elif codec_type == "audio":
                sample_rate = int(stream.get("sample_rate", 44100))
                channels = int(stream.get("channels", 2))
                stream_dur = float(stream.get("duration", duration_seconds))
                if duration_seconds == 0.0:
                    duration_seconds = stream_dur

                audio_streams.append(
                    AudioStreamInfo(
                        index=int(stream.get("index", 1)),
                        codec_name=stream.get("codec_name", "unknown"),
                        sample_rate=sample_rate,
                        channels=channels,
                        duration_seconds=stream_dur,
                    )
                )

        if len(video_streams) == 0 and len(audio_streams) == 0:
            raise ValueError(f"El archivo no contiene streams de video ni de audio válidos: {media_path.name}")

        return MediaInfo(
            file_path=str(media_path),
            file_name=media_path.name,
            file_size_bytes=file_size_bytes,
            format_name=format_name,
            duration_seconds=duration_seconds,
            video_streams=video_streams,
            audio_streams=audio_streams,
            has_video=len(video_streams) > 0,
            has_audio=len(audio_streams) > 0,
        )

    @classmethod
    def _fallback_probe(cls, media_path: Path, file_size_bytes: int) -> MediaInfo:
        """Sonda precisa y exhaustiva mediante ffmpeg -i."""
        ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
        result = subprocess.run(
            [ffmpeg_exe, "-i", str(media_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        stderr = result.stderr

        if "Invalid data found" in stderr or "Error opening input" in stderr or "unknown format" in stderr:
            raise ValueError(f"Archivo multimedia corrupto o formato no soportado: {media_path.name}")

        # 1. Duración y formato
        dur = 0.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
        if dur_match:
            h, m, s = dur_match.groups()
            dur = int(h) * 3600 + int(m) * 60 + float(s)

        fmt_match = re.search(r"Input #0,\s*([^,]+),", stderr)
        format_name = fmt_match.group(1).strip() if fmt_match else "media"

        video_streams: list[VideoStreamInfo] = []
        audio_streams: list[AudioStreamInfo] = []

        for line in stderr.splitlines():
            line_str = line.strip()
            if not line_str.startswith("Stream #"):
                continue

            # Stream #0:0[0x1](und): Video: h264 ... 640x360 ... 30 fps
            if ": Video:" in line_str:
                idx_match = re.search(r"Stream #\d+:(\d+)", line_str)
                idx = int(idx_match.group(1)) if idx_match else 0

                codec_match = re.search(r"Video:\s*([a-zA-Z0-9_-]+)", line_str)
                codec = codec_match.group(1) if codec_match else "unknown"

                res_match = re.search(r"(\d{2,5})x(\d{2,5})", line_str)
                if res_match:
                    width, height = int(res_match.group(1)), int(res_match.group(2))
                else:
                    width, height = 1920, 1080

                fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", line_str)
                fps = float(fps_match.group(1)) if fps_match else 30.0

                video_streams.append(
                    VideoStreamInfo(
                        index=idx,
                        codec_name=codec,
                        width=width,
                        height=height,
                        aspect_ratio=_calculate_aspect_ratio(width, height),
                        fps=fps,
                        duration_seconds=dur,
                    )
                )

            # Stream #0:1[0x2](und): Audio: aac ... 44100 Hz, mono
            elif ": Audio:" in line_str:
                idx_match = re.search(r"Stream #\d+:(\d+)", line_str)
                idx = int(idx_match.group(1)) if idx_match else 1

                codec_match = re.search(r"Audio:\s*([a-zA-Z0-9_-]+)", line_str)
                codec = codec_match.group(1) if codec_match else "unknown"

                sr_match = re.search(r"(\d+)\s*Hz", line_str)
                sample_rate = int(sr_match.group(1)) if sr_match else 44100

                if "stereo" in line_str:
                    channels = 2
                elif "mono" in line_str:
                    channels = 1
                elif "5.1" in line_str:
                    channels = 6
                else:
                    ch_digits = re.search(r"(\d+)\s*channels", line_str)
                    channels = int(ch_digits.group(1)) if ch_digits else 2

                audio_streams.append(
                    AudioStreamInfo(
                        index=idx,
                        codec_name=codec,
                        sample_rate=sample_rate,
                        channels=channels,
                        duration_seconds=dur,
                    )
                )

        if len(video_streams) == 0 and len(audio_streams) == 0:
            raise ValueError(f"No se pudieron identificar streams de audio ni video válidos en: {media_path.name}")

        return MediaInfo(
            file_path=str(media_path),
            file_name=media_path.name,
            file_size_bytes=file_size_bytes,
            format_name=format_name,
            duration_seconds=dur,
            video_streams=video_streams,
            audio_streams=audio_streams,
            has_video=len(video_streams) > 0,
            has_audio=len(audio_streams) > 0,
        )
