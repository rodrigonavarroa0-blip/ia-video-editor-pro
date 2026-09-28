"""Motor de detección y seguimiento facial con MediaPipe y OpenCV (§24)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.logger import analysis_logger
from app.models.vision import BoundingBox, FaceTrack, FaceTrackPoint


class FaceTracker:
    """Detecta y rastrea rostros a lo largo del tiempo generando FaceTracks normalizados."""

    @classmethod
    def track_faces(
        cls,
        video_path: Path,
        sample_step: int = 2,
        min_detection_confidence: float = 0.5,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[FaceTrack]:
        """
        Analiza el video fotograma a fotograma (o cada sample_step frames para velocidad)
        y construye las trayectorias de cada sujeto detectado.

        Usa cap.grab() para frames saltados en vez de cap.read(), evitando la
        decodificación completa de frames intermedios (~40% más rápido en videos largos).
        """
        media_file = Path(video_path).resolve()
        if not media_file.exists():
            raise FileNotFoundError(f"Video no encontrado para face tracking: {media_file}")

        cap = cv2.VideoCapture(str(media_file))
        if not cap.isOpened():
            raise ValueError(f"No se pudo abrir el video con OpenCV: {media_file.name}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 1

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

        analysis_logger.info(f"Iniciando Face Tracking: {media_file.name} ({total_frames} frames, {width}x{height})")

        # Intentar cargar MediaPipe o CascadeClassifier como fallback
        mp_detector = cls._init_mediapipe(min_detection_confidence)
        cascade = None
        if mp_detector is None:
            cascade_cls = getattr(cv2, "CascadeClassifier", None)
            data_haarcascades = getattr(getattr(cv2, "data", None), "haarcascades", "")
            if cascade_cls and data_haarcascades:
                cascade = cascade_cls(data_haarcascades + "haarcascade_frontalface_default.xml")

        # Usar dict con lista mutable para los puntos de cada track
        tracks: dict[int, list[FaceTrackPoint]] = {}
        next_track_id = [1]  # Lista mutable para permitir modificación en métodos internos
        frame_idx = 0

        try:
            while True:
                if frame_idx % sample_step == 0:
                    # Leer y decodificar solo en frames a procesar
                    ret, frame = cap.read()
                    if not ret:
                        break

                    timestamp = round(frame_idx / fps, 3)
                    detected_boxes = cls._detect_faces_in_frame(frame, mp_detector, cascade)

                    # Asociar detecciones al track más cercano (algoritmo Greedy Nearest Neighbor)
                    cls._associate_detections(tracks, detected_boxes, timestamp, next_track_id)
                else:
                    # Avanzar sin decodificar el frame completo (grab es ~10x más rápido que read)
                    ret = cap.grab()
                    if not ret:
                        break

                frame_idx += 1
                if progress_callback and frame_idx % 30 == 0:
                    progress_callback(min(1.0, frame_idx / total_frames))
        finally:
            cap.release()
            if mp_detector is not None and hasattr(mp_detector, "close"):
                try:
                    mp_detector.close()
                except Exception as e:
                    analysis_logger.debug(f"Cierre de detector MediaPipe: {e}")

        # Construir lista de modelos FaceTrack
        result_tracks: list[FaceTrack] = []
        for track_id, points in tracks.items():
            if len(points) >= 2:  # Filtrar detecciones aisladas de un solo frame
                avg_conf = sum(p.confidence for p in points) / len(points)
                result_tracks.append(
                    FaceTrack(
                        track_id=track_id,
                        points=points,
                        average_confidence=round(avg_conf, 2),
                    )
                )

        analysis_logger.info(f"Face tracking completado: {len(result_tracks)} sujetos rastreados.")
        return result_tracks

    @classmethod
    def _init_mediapipe(cls, min_conf: float):
        """Inicializa el detector de rostros de MediaPipe si está disponible."""
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
                return mp.solutions.face_detection.FaceDetection(
                    model_selection=1,  # 1 = Full-range (rostros lejanos y cercanos)
                    min_detection_confidence=min_conf,
                )
        except Exception as e:
            analysis_logger.debug(f"MediaPipe FaceDetection no disponible ({e}), usando CascadeClassifier.")
        return None

    @classmethod
    def _detect_faces_in_frame(
        cls,
        frame: np.ndarray,
        mp_detector: Any | None,
        cascade: Any | None,
    ) -> list[tuple[BoundingBox, float]]:
        """Detecta rostros en un fotograma y retorna BoundingBoxes normalizadas [0.0, 1.0]."""
        h, w = frame.shape[:2]
        results = []

        if mp_detector is not None:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_results = mp_detector.process(rgb_frame)
                if mp_results.detections:
                    for det in mp_results.detections:
                        box = det.location_data.relative_bounding_box
                        conf = det.score[0] if det.score else 0.9
                        bbox = BoundingBox(
                            x_min=round(max(0.0, min(1.0, float(box.xmin))), 4),
                            y_min=round(max(0.0, min(1.0, float(box.ymin))), 4),
                            width=round(max(0.0, min(1.0, float(box.width))), 4),
                            height=round(max(0.0, min(1.0, float(box.height))), 4),
                        )
                        results.append((bbox, float(conf)))
                    return results
            except Exception as e:
                analysis_logger.debug(f"Error procesando frame con MediaPipe: {e}")

        if cascade is not None and not getattr(cascade, "empty", lambda: True)():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(30, 30))
            for (x, y, fw, fh) in faces:
                bbox = BoundingBox(
                    x_min=round(x / w, 4),
                    y_min=round(y / h, 4),
                    width=round(fw / w, 4),
                    height=round(fh / h, 4),
                )
                results.append((bbox, 0.85))

        return results

    @classmethod
    def _associate_detections(
        cls,
        tracks: dict[int, list[FaceTrackPoint]],
        detections: list[tuple[BoundingBox, float]],
        timestamp: float,
        next_track_id: list[int],  # Lista mutable para permitir mutación correcta
    ) -> None:
        """Asocia detecciones a tracks existentes o inicia nuevos tracks."""
        unassigned_detections = list(detections)

        # Para cada track existente, buscar la detección más cercana
        for points in tracks.values():
            if not points or not unassigned_detections:
                continue

            last_point = points[-1]
            if timestamp - last_point.timestamp > 1.5:
                continue

            best_idx = -1
            best_dist = 0.25

            for idx, (bbox, _) in enumerate(unassigned_detections):
                center_x = bbox.x_min + (bbox.width / 2.0)
                center_y = bbox.y_min + (bbox.height / 2.0)
                dist = np.sqrt((center_x - last_point.center_x)**2 + (center_y - last_point.center_y)**2)

                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx >= 0:
                bbox, conf = unassigned_detections.pop(best_idx)
                c_x = bbox.x_min + (bbox.width / 2.0)
                c_y = bbox.y_min + (bbox.height / 2.0)
                points.append(
                    FaceTrackPoint(
                        timestamp=timestamp,
                        bbox=bbox,
                        center_x=round(c_x, 4),
                        center_y=round(c_y, 4),
                        confidence=round(conf, 2),
                        is_speaking=True,
                    )
                )

        # Crear nuevos tracks para detecciones no asociadas
        for bbox, conf in unassigned_detections:
            c_x = bbox.x_min + (bbox.width / 2.0)
            c_y = bbox.y_min + (bbox.height / 2.0)
            tid = next_track_id[0]
            tracks[tid] = [
                FaceTrackPoint(
                    timestamp=timestamp,
                    bbox=bbox,
                    center_x=round(c_x, 4),
                    center_y=round(c_y, 4),
                    confidence=round(conf, 2),
                    is_speaking=True,
                )
            ]
            next_track_id[0] += 1
