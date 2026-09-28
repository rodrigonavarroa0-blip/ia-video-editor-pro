"""Detector de cambios de plano y cortes de escena con visión clásica (OpenCV)."""

from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from app.core.logger import analysis_logger
from app.models.editorial import SceneBoundary


class SceneDetector:
    """Detecta cortes de escena analizando diferencias de histogramas HSV y diferencias inter-frame."""

    @classmethod
    def detect_scenes(
        cls,
        video_path: Path,
        threshold: float = 0.35,
        min_scene_duration_sec: float = 0.5,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[SceneBoundary]:
        """
        Analiza un archivo de video (preferentemente proxy 720p para máxima velocidad)
        y detecta los límites temporales de cada plano cinematográfico.
        """
        media_file = Path(video_path).resolve()
        if not media_file.exists():
            raise FileNotFoundError(f"Video no encontrado para detección de escenas: {media_file}")

        cap = cv2.VideoCapture(str(media_file))
        if not cap.isOpened():
            raise ValueError(f"No se pudo abrir el video con OpenCV: {media_file.name}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 1

        total_duration = total_frames / fps

        analysis_logger.info(f"Iniciando detección de escenas: {media_file.name} ({total_frames} frames a {fps:.1f} fps)")

        cut_timestamps: list[float] = [0.0]
        cut_scores: list[float] = [1.0]

        prev_hist: np.ndarray | None = None
        frame_idx = 0

        # Parámetros optimizados para histograma HSV
        h_bins, s_bins = 30, 32
        hist_size = [h_bins, s_bins]
        h_ranges = [0, 180]
        s_ranges = [0, 256]
        ranges = h_ranges + s_ranges
        channels = [0, 1]

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_time = frame_idx / fps

                # Reducir a resolución compacta 320x180 para velocidad extrema
                if frame.shape[1] > 320:
                    frame_small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
                else:
                    frame_small = frame

                hsv = cv2.cvtColor(frame_small, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], channels, None, hist_size, ranges, accumulate=False)
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                if prev_hist is not None:
                    # Correlación de histogramas: 1.0 = idénticos, 0.0 = diferentes
                    correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    difference = 1.0 - max(0.0, correlation)

                    time_since_last_cut = current_time - cut_timestamps[-1]

                    # Si la diferencia supera el umbral y ha pasado la duración mínima
                    if difference >= threshold and time_since_last_cut >= min_scene_duration_sec:
                        cut_timestamps.append(round(current_time, 3))
                        cut_scores.append(round(min(1.0, difference), 3))
                        analysis_logger.debug(f"Corte detectado en {current_time:.2f}s (diff={difference:.3f})")

                prev_hist = hist
                frame_idx += 1

                if progress_callback and frame_idx % 30 == 0:
                    progress_callback(min(1.0, frame_idx / total_frames))
        finally:
            cap.release()

        # Añadir timestamp final
        if cut_timestamps[-1] < total_duration:
            cut_timestamps.append(round(total_duration, 3))
            cut_scores.append(1.0)

        # Construir lista de SceneBoundary
        scenes: list[SceneBoundary] = []
        for i in range(len(cut_timestamps) - 1):
            start = cut_timestamps[i]
            end = cut_timestamps[i + 1]
            duration = max(0.0, end - start)
            score = cut_scores[i] if i < len(cut_scores) else 0.8

            if duration > 0.05:  # Filtrar escenas microscópicas
                scenes.append(
                    SceneBoundary(
                        start=round(start, 3),
                        end=round(end, 3),
                        duration=round(duration, 3),
                        score=round(score, 3),
                    )
                )

        # Si el video es continuo y no hubo cortes, la escena es el video completo
        if not scenes:
            scenes.append(
                SceneBoundary(
                    start=0.0,
                    end=round(total_duration, 3),
                    duration=round(total_duration, 3),
                    score=1.0,
                )
            )

        analysis_logger.info(f"Detección de escenas completada: {len(scenes)} planos identificados.")
        return scenes
