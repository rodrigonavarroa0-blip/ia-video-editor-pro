"""Motor de renderizado final y codificación acelerada por hardware (§38, §39)."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import ClassVar

from app.analyzers.media_probe import MediaProbe
from app.core.logger import render_logger
from app.models.timeline import VirtualTimeline
from app.render.conform_engine import ConformEngine
from app.utils.ffmpeg import FFmpegManager


class RenderEngine:
    """Ejecuta el renderizado de alta fidelidad conformando los cortes a RAW."""

    PRESETS: ClassVar[dict[str, dict]] = {
        "social": {
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "crf": 20,
            "audio_bitrate": "192k",
            "burn_subs": True,
        },
        "master": {
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "crf": 16,
            "audio_bitrate": "320k",
            "burn_subs": False,
        },
        "preview": {
            "width": 720,
            "height": 1280,
            "fps": 30.0,
            "crf": 24,
            "audio_bitrate": "128k",
            "burn_subs": True,
        },
    }

    @classmethod
    def render_timeline(
        cls,
        timeline: VirtualTimeline,
        raw_source_path: Path,
        output_file: Path,
        audio_file: Path | None = None,
        subtitle_file: Path | None = None,
        preset_name: str = "social",
        encoder: str | None = None,
    ) -> dict:
        """
        Renderiza el VirtualTimeline conformando directamente al material RAW.
        """
        raw_src = Path(raw_source_path).resolve()
        out_vid = Path(output_file).resolve()
        out_vid.parent.mkdir(parents=True, exist_ok=True)

        if not raw_src.exists():
            raise FileNotFoundError(f"Video fuente RAW no encontrado: {raw_src}")

        preset = cls.PRESETS.get(preset_name.lower(), cls.PRESETS["social"])
        t_width = preset["width"]
        t_height = preset["height"]

        # 1. Obtener resolución real del archivo RAW
        raw_probe = MediaProbe.probe(raw_src)
        src_w = raw_probe.primary_video.width if raw_probe.primary_video else 1920
        src_h = raw_probe.primary_video.height if raw_probe.primary_video else 1080

        # Subtítulos a quemar según preset
        sub_to_burn = subtitle_file if preset["burn_subs"] else None

        # 2. Construir grafo de filtros
        filter_str, final_vmap = ConformEngine.build_filter_complex(
            timeline=timeline,
            source_width=src_w,
            source_height=src_h,
            target_width=t_width,
            target_height=t_height,
            subtitle_file=sub_to_burn,
        )

        ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
        selected_vcodec = encoder or FFmpegManager.get_optimal_video_encoder()

        render_logger.info(
            f"Iniciando Render Final: {out_vid.name} ({t_width}x{t_height} @ {preset['fps']}fps, "
            f"Encoder: {selected_vcodec}, Preset: {preset_name})"
        )

        cmd = [ffmpeg_exe, "-y", "-i", str(raw_src)]

        has_ext_audio = False
        if audio_file and Path(audio_file).exists():
            cmd.extend(["-i", str(Path(audio_file).resolve())])
            has_ext_audio = True

        cmd.extend([
            "-filter_complex", filter_str,
            "-map", final_vmap,
        ])

        if has_ext_audio:
            cmd.extend(["-map", "1:a:0"])
        else:
            cmd.extend(["-map", "0:a:0?"])

        # Parámetros de codificación de video
        if selected_vcodec == "h264_videotoolbox":
            cmd.extend([
                "-c:v", "h264_videotoolbox",
                "-b:v", "10M",
                "-allow_sw", "1",
                "-pix_fmt", "yuv420p",
            ])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-crf", str(preset["crf"]),
                "-preset", "medium" if preset_name != "preview" else "ultrafast",
                "-pix_fmt", "yuv420p",
            ])

        # Parámetros de codificación de audio
        cmd.extend([
            "-c:a", "aac",
            "-b:a", preset["audio_bitrate"],
            "-ar", "44100",
            "-shortest",
            str(out_vid),
        ])

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode("utf-8", errors="replace")
            if selected_vcodec != "libx264":
                render_logger.warning(f"Fallo encoder hardware {selected_vcodec}, reintentando con libx264...")
                # Reemplazar con libx264 y reintentar
                vcodec_idx = cmd.index("-c:v")
                cmd[vcodec_idx + 1] = "libx264"
                if "-b:v" in cmd:
                    b_idx = cmd.index("-b:v")
                    cmd[b_idx] = "-crf"
                    cmd[b_idx + 1] = "20"
                if "-allow_sw" in cmd:
                    sw_idx = cmd.index("-allow_sw")
                    del cmd[sw_idx:sw_idx + 2]
                subprocess.run(cmd, capture_output=True, check=True)
            else:
                render_logger.error(f"Error de renderizado FFmpeg: {err_msg}")
                raise RuntimeError(f"Fallo en render final FFmpeg: {err_msg}")

        # 3. Calcular metadatos del render con lectura de hash en bloques (sin saturar memoria)
        out_probe = MediaProbe.probe(out_vid)
        file_size = out_vid.stat().st_size

        hasher = hashlib.sha256()
        with open(out_vid, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        metadata = {
            "output_file": str(out_vid),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "duration_seconds": round(out_probe.duration_seconds, 2),
            "width": out_probe.primary_video.width if out_probe.primary_video else t_width,
            "height": out_probe.primary_video.height if out_probe.primary_video else t_height,
            "fps": round(out_probe.primary_video.fps, 2) if out_probe.primary_video else preset["fps"],
            "video_codec": out_probe.primary_video.codec_name if out_probe.primary_video else selected_vcodec,
            "audio_codec": out_probe.primary_audio.codec_name if out_probe.primary_audio else "aac",
            "preset_applied": preset_name,
            "burned_subtitles": preset["burn_subs"] and (sub_to_burn is not None),
            "sha256": sha256_hash,
        }

        render_meta_path = out_vid.parent / "render_metadata.json"
        with open(render_meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        render_logger.info(f"Render Final completado exitosamente: {out_vid.name} ({metadata['file_size_mb']} MB)")
        return metadata
