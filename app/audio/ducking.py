"""Procesador de auto-ducking musical y mezcla adaptativa (§28)."""

from pathlib import Path

import numpy as np

from app.audio.loudness import LoudnessProcessor
from app.core.logger import render_logger


class DuckingProcessor:
    """Atenúa automáticamente la música de fondo cuando se detecta presencia de voz."""

    @classmethod
    def generate_ducking_envelope(
        cls,
        total_samples: int,
        sample_rate: int,
        speech_intervals: list[tuple[float, float]],
        base_gain_db: float = -4.0,
        ducked_gain_db: float = -16.0,
        attack_ms: float = 150.0,
        release_ms: float = 400.0,
    ) -> np.ndarray:
        """Genera una envolvente de volumen continua y suave para la pista de música."""
        envelope = np.ones(total_samples, dtype=np.float32) * (10.0 ** (base_gain_db / 20.0))
        ducked_linear = 10.0 ** (ducked_gain_db / 20.0)
        base_linear = 10.0 ** (base_gain_db / 20.0)

        attack_samples = max(1, int(sample_rate * (attack_ms / 1000.0)))
        release_samples = max(1, int(sample_rate * (release_ms / 1000.0)))

        for start_sec, end_sec in speech_intervals:
            s_idx = max(0, int(start_sec * sample_rate))
            e_idx = min(total_samples, int(end_sec * sample_rate))

            # Ataque (fade down antes y durante el inicio)
            att_start = max(0, s_idx - attack_samples)
            att_len = s_idx - att_start
            if att_len > 0:
                ramp_down = np.linspace(base_linear, ducked_linear, att_len)
                envelope[att_start:s_idx] = np.minimum(envelope[att_start:s_idx], ramp_down)

            # Sostenimiento atenuado durante el habla
            envelope[s_idx:e_idx] = ducked_linear

            # Relajación (fade up tras el final)
            rel_end = min(total_samples, e_idx + release_samples)
            rel_len = rel_end - e_idx
            if rel_len > 0:
                ramp_up = np.linspace(ducked_linear, base_linear, rel_len)
                envelope[e_idx:rel_end] = np.minimum(envelope[e_idx:rel_end], ramp_up)

        return envelope

    @classmethod
    def mix_voice_and_music(
        cls,
        voice_wav: Path,
        music_wav: Path,
        output_wav: Path,
        speech_intervals: list[tuple[float, float]],
        base_music_gain_db: float = -6.0,
        ducked_music_gain_db: float = -18.0,
    ) -> Path:
        """Mezcla la pista vocal prioritaria con la música de fondo atenuada por sidechain ducking."""
        sr_voice, voice_audio = LoudnessProcessor.read_wav(voice_wav)
        sr_music, music_audio = LoudnessProcessor.read_wav(music_wav)

        render_logger.info(f"Mezclando voz con música de fondo ducking: {voice_wav.name} + {music_wav.name}")

        # Ajustar longitud de la música para coincidir con la voz
        target_len = len(voice_audio)
        if len(music_audio) < target_len:
            # Repetir en bucle si la música es más corta
            repeats = int(np.ceil(target_len / len(music_audio)))
            music_audio = np.tile(music_audio, repeats)[:target_len]
        else:
            music_audio = music_audio[:target_len]

        envelope = cls.generate_ducking_envelope(
            total_samples=target_len,
            sample_rate=sr_voice,
            speech_intervals=speech_intervals,
            base_gain_db=base_music_gain_db,
            ducked_gain_db=ducked_music_gain_db,
        )

        ducked_music = music_audio * envelope
        mixed = voice_audio + ducked_music

        # Normalizar para evitar clipping de la suma
        peak = np.max(np.abs(mixed))
        if peak > 0.98:
            mixed = mixed * (0.98 / peak)

        return LoudnessProcessor.write_wav(output_wav, sr_voice, mixed)
