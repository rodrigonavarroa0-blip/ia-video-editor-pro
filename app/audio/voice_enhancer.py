"""Realce y acondicionamiento vocal profesional con DSP (EQ, High-Pass y Compresión) (§27)."""

from pathlib import Path

import numpy as np
from scipy import signal

from app.audio.loudness import LoudnessProcessor
from app.core.logger import render_logger


class VoiceEnhancer:
    """Aplica filtros de acondicionamiento acústico para maximizar la inteligibilidad vocal."""

    @classmethod
    def enhance_voice_track(
        cls,
        input_wav: Path,
        output_wav: Path,
        high_pass_hz: float = 80.0,
        compression_threshold_db: float = -20.0,
        compression_ratio: float = 3.0,
    ) -> Path:
        """
        Aplica la cadena de masterización vocal:
        1. High-Pass Filter a 80Hz para eliminar ruidos de viento y resonancias graves.
        2. EQ de presencia (atenuación en 350Hz, realce en 4.5kHz).
        3. Compresor dinámico suave para nivelación vocal.
        """
        sample_rate, audio = LoudnessProcessor.read_wav(input_wav)
        if len(audio) == 0:
            return LoudnessProcessor.write_wav(output_wav, sample_rate, audio)

        render_logger.info(f"Aplicando Voice Enhancement DSP a: {input_wav.name}")

        # 1. Filtro Pasa-Altos (High-Pass 80Hz Butterworth de 2º orden)
        nyquist = sample_rate / 2.0
        hp_freq = min(0.95, high_pass_hz / nyquist)
        sos_hp = signal.butter(2, hp_freq, btype="highpass", output="sos")
        audio_filtered = signal.sosfilt(sos_hp, audio)

        # 2. EQ Paramétrica de Presencia Vocal
        # Atenuación de resonancias en 350Hz (notch / peak filter suave)
        audio_eq = cls._apply_peaking_filter(audio_filtered, sample_rate, center_freq=350.0, gain_db=-2.5, q=1.0)
        # Realce de aire y presencia en 4500Hz
        audio_eq = cls._apply_peaking_filter(audio_eq, sample_rate, center_freq=4500.0, gain_db=2.0, q=1.2)

        # 3. Compresor Dinámico Suave (RMS Dynamic Compressor)
        audio_compressed = cls._apply_dynamic_compression(
            audio_eq,
            sample_rate,
            threshold_db=compression_threshold_db,
            ratio=compression_ratio,
        )

        out = LoudnessProcessor.write_wav(output_wav, sample_rate, audio_compressed)
        render_logger.info(f"Voice Enhancement completado: {out.name}")
        return out

    @classmethod
    def _apply_peaking_filter(
        cls,
        audio: np.ndarray,
        sample_rate: int,
        center_freq: float,
        gain_db: float,
        q: float = 1.0,
    ) -> np.ndarray:
        """Aplica un filtro paramétrico de campana (Peaking/Bell EQ) biquad."""
        nyquist = sample_rate / 2.0
        if center_freq >= nyquist:
            return audio

        w0 = 2.0 * np.pi * center_freq / sample_rate
        alpha = np.sin(w0) / (2.0 * q)
        a = 10.0 ** (gain_db / 40.0)

        b0 = 1.0 + alpha * a
        b1 = -2.0 * np.cos(w0)
        b2 = 1.0 - alpha * a
        a0 = 1.0 + alpha / a
        a1 = -2.0 * np.cos(w0)
        a2 = 1.0 - alpha / a

        b = np.array([b0, b1, b2]) / a0
        a_arr = np.array([a0, a1, a2]) / a0

        return signal.lfilter(b, a_arr, audio).astype(np.float32)

    @classmethod
    def _apply_dynamic_compression(
        cls,
        audio: np.ndarray,
        sample_rate: int,
        threshold_db: float = -20.0,
        ratio: float = 3.0,
        attack_ms: float = 15.0,
        release_ms: float = 100.0,
    ) -> np.ndarray:
        """Aplica compresión dinámica suave para estabilizar el rango dinámico de la voz."""
        threshold_linear = 10.0 ** (threshold_db / 20.0)
        attack_coeff = np.exp(-1.0 / (sample_rate * (attack_ms / 1000.0)))
        release_coeff = np.exp(-1.0 / (sample_rate * (release_ms / 1000.0)))

        envelope = 0.0
        gain_curve = np.ones_like(audio)

        for i in range(len(audio)):
            input_level = abs(audio[i])
            if input_level > envelope:
                envelope = attack_coeff * envelope + (1.0 - attack_coeff) * input_level
            else:
                envelope = release_coeff * envelope + (1.0 - release_coeff) * input_level

            if envelope > threshold_linear and envelope > 1e-9:
                env_db = 20.0 * np.log10(envelope)
                overshoot_db = env_db - threshold_db
                compressed_db = threshold_db + (overshoot_db / ratio)
                gain_db = compressed_db - env_db
                gain_curve[i] = 10.0 ** (gain_db / 20.0)

        compressed_audio = audio * gain_curve
        return compressed_audio.astype(np.float32)
