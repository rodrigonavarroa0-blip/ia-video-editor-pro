"""Analizador multinivel de silencios y pausas acústicas (§15)."""

import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.core.logger import analysis_logger
from app.models.editorial import SilenceInterval, SilenceSeverity


class SilenceDetector:
    """Detecta intervalos de silencio y clasifica su severidad con base en energía RMS (dBFS)."""

    @classmethod
    def detect_silence(
        cls,
        audio_path: Path,
        threshold_db: float = -38.0,
        frame_duration_ms: int = 20,
        min_silence_duration_sec: float = 0.15,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[SilenceInterval]:
        """
        Analiza un archivo de audio WAV y retorna los intervalos de silencio clasificados
        en niveles KEEP, EVALUATE, CUT_SUGGESTED y CUT_AGGRESSIVE.
        """
        wav_file = Path(audio_path).resolve()
        if not wav_file.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {wav_file}")

        analysis_logger.info(f"Iniciando análisis de silencios: {wav_file.name} (umbral={threshold_db} dBFS)")

        # Leer audio WAV usando el módulo estándar wave
        with wave.open(str(wav_file), "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            num_frames = wf.getnframes()
            raw_bytes = wf.readframes(num_frames)

        if num_frames == 0:
            return []

        # Convertir a numpy array normalizado (-1.0 a 1.0)
        if sample_width == 2:
            samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            samples = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            samples = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

        # Si es estéreo, mezclar a mono promediando canales
        if num_channels > 1:
            samples = samples.reshape(-1, num_channels).mean(axis=1)

        total_duration = len(samples) / sample_rate
        samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        if samples_per_frame <= 0:
            samples_per_frame = 1

        total_windows = len(samples) // samples_per_frame

        # Calcular RMS y dBFS por frame
        is_silent_frame = []
        frame_db_levels = []

        for i in range(total_windows):
            start_idx = i * samples_per_frame
            end_idx = start_idx + samples_per_frame
            chunk = samples[start_idx:end_idx]

            rms = np.sqrt(np.mean(chunk**2) + 1e-12)
            dbfs = 20.0 * np.log10(rms)

            is_silent = dbfs < threshold_db
            is_silent_frame.append(is_silent)
            frame_db_levels.append(dbfs)

            if progress_callback and i % 500 == 0 and total_windows > 0:
                progress_callback(min(1.0, i / total_windows))

        # Agrupar frames silenciosos contiguos en intervalos
        raw_intervals = []
        in_silence = False
        silence_start = 0.0
        db_accumulator = []

        for i, silent in enumerate(is_silent_frame):
            frame_time = i * (frame_duration_ms / 1000.0)

            if silent and not in_silence:
                in_silence = True
                silence_start = frame_time
                db_accumulator = [frame_db_levels[i]]
            elif silent and in_silence:
                db_accumulator.append(frame_db_levels[i])
            elif not silent and in_silence:
                in_silence = False
                silence_end = frame_time
                dur = silence_end - silence_start
                avg_db = float(np.mean(db_accumulator)) if db_accumulator else threshold_db
                if dur >= min_silence_duration_sec:
                    raw_intervals.append((silence_start, silence_end, dur, avg_db))
                db_accumulator = []

        # Si terminó en silencio
        if in_silence:
            silence_end = total_duration
            dur = silence_end - silence_start
            avg_db = float(np.mean(db_accumulator)) if db_accumulator else threshold_db
            if dur >= min_silence_duration_sec:
                raw_intervals.append((silence_start, silence_end, dur, avg_db))

        # Clasificación multinivel (§15)
        silence_intervals: list[SilenceInterval] = []
        for start, end, duration, avg_db in raw_intervals:
            if duration < 0.25:
                severity = SilenceSeverity.KEEP
            elif 0.25 <= duration < 0.50:
                severity = SilenceSeverity.EVALUATE
            elif 0.50 <= duration < 1.00:
                severity = SilenceSeverity.CUT_SUGGESTED
            else:
                severity = SilenceSeverity.CUT_AGGRESSIVE

            silence_intervals.append(
                SilenceInterval(
                    start=round(start, 3),
                    end=round(end, 3),
                    duration=round(duration, 3),
                    severity=severity,
                    db_level=round(avg_db, 1),
                )
            )

        analysis_logger.info(
            f"Análisis de silencios completado: {len(silence_intervals)} intervalos detectados "
            f"({sum(1 for s in silence_intervals if s.severity == SilenceSeverity.CUT_AGGRESSIVE)} agresivos)."
        )
        return silence_intervals
