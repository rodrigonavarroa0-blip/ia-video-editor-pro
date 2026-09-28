"""Gestor de efectos sonoros (SFX Triggers) y síntesis procedural (§29)."""

from pathlib import Path

import numpy as np

from app.audio.loudness import LoudnessProcessor
from app.core.logger import render_logger
from app.models.editorial import EditAction, EditorialPlan
from app.models.transcript import TranscriptDocument


class SFXManager:
    """Dispara y sintetiza efectos sonoros contextuales para dinamismo editorial."""

    @classmethod
    def generate_synthetic_sfx(cls, sfx_type: str, output_path: Path, sample_rate: int = 44100) -> Path:
        """Sintetiza un efecto de sonido procedural limpio (whoosh, pop, ding, riser)."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if sfx_type == "whoosh":
            # Barrido de ruido blanco con envolvente gaussiana
            duration = 0.25
            n_samples = int(sample_rate * duration)
            t = np.linspace(0, 1, n_samples)
            noise = np.random.uniform(-1, 1, n_samples)
            env = np.sin(np.pi * t) ** 2
            audio = noise * env * 0.4

        elif sfx_type == "pop":
            # Clic tonal percusivo corto
            duration = 0.08
            n_samples = int(sample_rate * duration)
            t = np.linspace(0, duration, n_samples)
            freq = np.linspace(300, 150, n_samples)
            sine = np.sin(2 * np.pi * freq * t)
            env = np.exp(-t * 50)
            audio = sine * env * 0.6

        elif sfx_type in ("ding", "chime"):
            # Campana cristalina con armónicos y decaimiento exponencial
            duration = 0.50
            n_samples = int(sample_rate * duration)
            t = np.linspace(0, duration, n_samples)
            f1, f2 = 1200.0, 2400.0
            sine = 0.7 * np.sin(2 * np.pi * f1 * t) + 0.3 * np.sin(2 * np.pi * f2 * t)
            env = np.exp(-t * 8)
            audio = sine * env * 0.5

        else:
            # Tono genérico
            duration = 0.15
            n_samples = int(sample_rate * duration)
            t = np.linspace(0, duration, n_samples)
            audio = np.sin(2 * np.pi * 440 * t) * np.exp(-t * 10) * 0.4

        return LoudnessProcessor.write_wav(out, sample_rate, audio.astype(np.float32))

    @classmethod
    def plan_sfx_cues(cls, plan: EditorialPlan, transcript: TranscriptDocument | None = None) -> list[dict]:
        """Genera la lista de marcas temporales para inserción de SFX según decisiones de edición."""
        cues = []

        for d in plan.decisions:
            if d.action == EditAction.ZOOM_IN:
                s_in = d.source_in if d.source_in is not None else 0.0
                cues.append({
                    "timestamp": s_in,
                    "sfx_type": "whoosh",
                    "volume_db": -16.0,
                    "reason": "Transición Punch-in Zoom",
                })
            elif d.action == EditAction.EMPHASIZE:
                s_in = d.source_in if d.source_in is not None else 0.0
                cues.append({
                    "timestamp": s_in,
                    "sfx_type": "pop",
                    "volume_db": -14.0,
                    "reason": "Énfasis visual",
                })

        render_logger.info(f"Planificación de SFX completada: {len(cues)} disparadores asignados.")
        return cues
