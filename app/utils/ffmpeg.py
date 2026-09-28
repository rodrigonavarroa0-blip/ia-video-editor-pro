"""Wrapper seguro para ejecución y descubrimiento de FFmpeg y FFprobe."""

import logging
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable

import imageio_ffmpeg

ffmpeg_logger = logging.getLogger("iva.ffmpeg")


class FFmpegError(Exception):
    """Excepción lanzada cuando un comando de FFmpeg falla."""


class FFmpegManager:
    """Gestiona la detección de binarios, aceleración por hardware y ejecución segura de FFmpeg."""

    _ffmpeg_path: str | None = None
    _ffprobe_path: str | None = None
    _has_videotoolbox: bool | None = None

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """Obtiene la ruta absoluta al ejecutable de ffmpeg."""
        if cls._ffmpeg_path is not None:
            return cls._ffmpeg_path

        # 1. Buscar en PATH del sistema
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            cls._ffmpeg_path = system_ffmpeg
            return cls._ffmpeg_path

        # 2. Buscar en /opt/homebrew/bin/ffmpeg o /usr/local/bin/ffmpeg
        for standard_path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.exists(standard_path) and os.access(standard_path, os.X_OK):
                cls._ffmpeg_path = standard_path
                return cls._ffmpeg_path

        # 3. Fallback a imageio-ffmpeg
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                cls._ffmpeg_path = exe
                return cls._ffmpeg_path
        except Exception as e:
            ffmpeg_logger.debug(f"imageio-ffmpeg no disponible: {e}")

        raise FileNotFoundError("No se pudo encontrar un binario ejecutable de FFmpeg en el sistema.")

    @classmethod
    def has_ffprobe(cls) -> bool:
        """Determina si existe un binario real de ffprobe disponible."""
        return cls.get_ffprobe_path() is not None

    @classmethod
    def get_ffprobe_path(cls) -> str | None:
        """Obtiene la ruta a ffprobe si está disponible en el sistema, o None si no existe."""
        if cls._ffprobe_path is not None:
            return cls._ffprobe_path

        # 1. Buscar en PATH
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            cls._ffprobe_path = system_ffprobe
            return cls._ffprobe_path

        for standard_path in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"]:
            if os.path.exists(standard_path) and os.access(standard_path, os.X_OK):
                cls._ffprobe_path = standard_path
                return cls._ffprobe_path

        return None

    @classmethod
    def has_videotoolbox(cls) -> bool:
        """Comprueba si el codificador h264_videotoolbox de Apple Silicon está disponible."""
        if cls._has_videotoolbox is not None:
            return cls._has_videotoolbox

        if sys.platform != "darwin":
            cls._has_videotoolbox = False
            return False

        try:
            ffmpeg_exe = cls.get_ffmpeg_path()
            result = subprocess.run(
                [ffmpeg_exe, "-encoders"],
                capture_output=True,
                text=True,
                check=False,
            )
            cls._has_videotoolbox = "h264_videotoolbox" in result.stdout
        except Exception as e:
            ffmpeg_logger.debug(f"Error verificando VideoToolbox: {e}")
            cls._has_videotoolbox = False

        return cls._has_videotoolbox

    @classmethod
    def get_optimal_video_encoder(cls) -> str:
        """Retorna h264_videotoolbox si está soportado, o libx264 en su defecto."""
        return "h264_videotoolbox" if cls.has_videotoolbox() else "libx264"

    @classmethod
    def run_command(
        cls,
        args: list[str],
        duration_seconds: float | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> tuple[str, str]:
        """
        Ejecuta un comando de FFmpeg de forma segura con captura de stderr,
        registro en logs/ffmpeg.log y cálculo de progreso en tiempo real.
        """
        ffmpeg_exe = cls.get_ffmpeg_path()
        full_cmd = [ffmpeg_exe] + args
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in full_cmd)

        ffmpeg_logger.debug(f"Ejecutando: {cmd_str}")

        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        stderr_lines: list[str] = []
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        if process.stderr:
            for line in process.stderr:
                stderr_lines.append(line)
                if progress_callback and duration_seconds and duration_seconds > 0:
                    match = time_pattern.search(line)
                    if match:
                        hours, minutes, seconds = match.groups()
                        current_sec = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        progress = min(1.0, max(0.0, current_sec / duration_seconds))
                        progress_callback(progress)

        stdout, _ = process.communicate()
        stderr = "".join(stderr_lines)

        if process.returncode != 0:
            ffmpeg_logger.error(f"Error FFmpeg (código {process.returncode}):\n{stderr}")
            raise FFmpegError(f"FFmpeg falló con código {process.returncode}:\n{stderr[-1000:]}")

        return stdout, stderr
