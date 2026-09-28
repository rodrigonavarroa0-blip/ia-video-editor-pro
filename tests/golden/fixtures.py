"""Generadores de videos de referencia sintéticos para la suite de Golden Tests (§101)."""

import subprocess
from pathlib import Path

from app.utils.ffmpeg import FFmpegManager


def create_golden_dynamic_monologue(out_path: Path) -> Path:
    """Genera un video sintético de 6.0s con audio continuo para simular un monólogo dinámico."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    out = Path(out_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=0x161a26:duration=6.0:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6.0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out


def create_golden_hesitant_speech(out_path: Path) -> Path:
    """Genera un video sintético de 8.0s con 3 pausas de silencio prolongadas (>1.2s)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    out = Path(out_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=0x0a0c10:duration=8.0:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=520:duration=1.5",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono,atrim=duration=1.5",
        "-f", "lavfi", "-i", "sine=frequency=520:duration=2.0",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono,atrim=duration=1.5",
        "-f", "lavfi", "-i", "sine=frequency=520:duration=1.5",
        "-filter_complex",
        "[1:a][2:a][3:a][4:a][5:a]concat=n=5:v=0:a=1[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out


def create_golden_multi_shot(out_path: Path) -> Path:
    """Genera un video sintético de 6.0s con 3 cambios drásticos de plano (Rojo 2s, Verde 2s, Azul 2s)."""
    ffmpeg_exe = FFmpegManager.get_ffmpeg_path()
    out = Path(out_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=red:duration=2.0:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "color=c=green:duration=2.0:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "color=c=blue:duration=2.0:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=660:duration=6.0",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0[vout]",
        "-map", "[vout]",
        "-map", "3:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out
