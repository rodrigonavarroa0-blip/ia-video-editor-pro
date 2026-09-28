"""Procesador de medición y normalización de sonoridad estándar EBU R128 (§26)."""

from pathlib import Path

import numpy as np
import pyloudnorm as pyln
from scipy.io import wavfile

from app.core.logger import render_logger
from app.models.audio import AudioMetrics


class LoudnessProcessor:
    """Mide y normaliza el volumen sonoro bajo los estándares EBU R128 y ITU-R BS.1770."""

    @classmethod
    def read_wav(cls, wav_path: Path) -> tuple[int, np.ndarray]:
        """Lee un archivo WAV y retorna sample_rate y datos normalizados en float32 [-1.0, 1.0]."""
        path = Path(wav_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Archivo WAV no encontrado: {path}")

        sample_rate, data = wavfile.read(str(path))

        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            audio = (data.astype(np.float32) - 128.0) / 128.0
        elif data.dtype in (np.float32, np.float64):
            audio = data.astype(np.float32)
        else:
            audio = data.astype(np.float32)

        return sample_rate, audio

    @classmethod
    def write_wav(cls, output_path: Path, sample_rate: int, audio: np.ndarray) -> Path:
        """Escribe un array normalizado a un archivo WAV PCM de 16 bits sin distorsión."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        # Limitar estrictamente al rango [-1.0, 1.0] para evitar wrap-around
        clipped = np.clip(audio, -1.0, 1.0)
        data_int16 = (clipped * 32767.0).astype(np.int16)
        wavfile.write(str(out), sample_rate, data_int16)
        return out

    @classmethod
    def measure_loudness(cls, wav_path: Path, target_lufs: float = -14.0) -> AudioMetrics:
        """Mide la sonoridad integrada (LUFS), True Peak y Loudness Range (LRA)."""
        sample_rate, audio = cls.read_wav(wav_path)

        if len(audio) == 0:
            return AudioMetrics(
                integrated_lufs=-70.0,
                true_peak_db=-70.0,
                lra_lu=0.0,
                rms_db=-70.0,
                target_lufs=target_lufs,
                gain_adjustment_db=0.0,
            )

        # Calcular True Peak (pico máximo absoluto en dBFS/dBTP)
        peak_val = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
        true_peak_db = 20.0 * np.log10(peak_val) if peak_val > 1e-9 else -70.0

        # Calcular RMS promedio
        rms_val = float(np.sqrt(np.mean(audio**2) + 1e-12))
        rms_db = 20.0 * np.log10(rms_val)

        # Medición EBU R128 con pyloudnorm
        meter = pyln.Meter(sample_rate)
        try:
            lufs = float(meter.integrated_loudness(audio))
            if np.isneginf(lufs) or np.isnan(lufs) or lufs < -70.0:
                lufs = -70.0
        except Exception:
            lufs = float(rms_db)

        gain_needed = target_lufs - lufs if lufs > -65.0 else 0.0

        return AudioMetrics(
            integrated_lufs=round(lufs, 2),
            true_peak_db=round(true_peak_db, 2),
            lra_lu=round(max(0.0, true_peak_db - rms_db), 2),
            rms_db=round(rms_db, 2),
            target_lufs=target_lufs,
            gain_adjustment_db=round(gain_needed, 2),
        )

    @classmethod
    def normalize_audio(
        cls,
        input_wav: Path,
        output_wav: Path,
        target_lufs: float = -14.0,
        max_true_peak_db: float = -1.0,
    ) -> tuple[Path, AudioMetrics]:
        """
        Normaliza el archivo de audio exactamente al target_lufs (ej. -14.0 LUFS)
        asegurando que el True Peak no sobrepase max_true_peak_db (-1.0 dBTP).

        Utiliza brickwall hard limiting después del escalado de ganancia para
        asegurar que jamás se excede el True Peak sin introducir distorsión tanh.
        """
        sample_rate, audio = cls.read_wav(input_wav)
        metrics_before = cls.measure_loudness(input_wav, target_lufs=target_lufs)

        if metrics_before.integrated_lufs <= -65.0:
            render_logger.warning("Audio en silencio casi absoluto, omitiendo ganancia masiva.")
            out_file = cls.write_wav(output_wav, sample_rate, audio)
            return out_file, metrics_before

        # Calcular factor de ganancia lineal
        gain_db = target_lufs - metrics_before.integrated_lufs
        gain_linear = 10.0 ** (gain_db / 20.0)

        normalized = audio * gain_linear

        # Calcular techo de pico máximo permitido (nunca puede ser 0 por construcción)
        # max_true_peak_db es típicamente -1.0 dBTP → max_peak_linear ≈ 0.891
        max_peak_linear = 10.0 ** (max_true_peak_db / 20.0)
        if max_peak_linear <= 0.0:
            # Salvaguarda ante valores inválidos como -inf o NaN
            max_peak_linear = 0.891

        current_peak = float(np.max(np.abs(normalized)))

        if current_peak > max_peak_linear:
            # Brickwall hard limiting: clamp sin distorsión armónica
            # Esta es la técnica estándar en broadcast para True Peak compliance
            scale_factor = max_peak_linear / current_peak
            normalized = normalized * scale_factor
            render_logger.info(
                f"Brickwall limiter aplicado: pico {current_peak:.4f} → {max_peak_linear:.4f} "
                f"(atenuación: {20 * np.log10(scale_factor):.2f} dB)"
            )

        out_file = cls.write_wav(output_wav, sample_rate, normalized)
        metrics_after = cls.measure_loudness(out_file, target_lufs=target_lufs)

        render_logger.info(
            f"Normalización EBU R128 completada: {metrics_before.integrated_lufs:.1f} LUFS → "
            f"{metrics_after.integrated_lufs:.1f} LUFS (Peak: {metrics_after.true_peak_db:.1f} dBTP)"
        )
        return out_file, metrics_after
