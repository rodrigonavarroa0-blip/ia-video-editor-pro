"""Motor de reencuadre inteligente 9:16 con suavizado dinámico y dead zones (§25)."""

import bisect

from app.core.logger import analysis_logger
from app.models.editorial import SceneBoundary
from app.models.vision import FaceTrack, ReframeKeyframe


class SmartReframer:
    """Calcula keyframes de recorte 9:16 centrados en el sujeto con suavizado temporal cinemático."""

    @classmethod
    def calculate_reframing_keyframes(
        cls,
        source_width: int,
        source_height: int,
        total_duration: float,
        face_tracks: list[FaceTrack],
        scenes: list[SceneBoundary] | None = None,
        target_aspect_ratio: str = "9:16",
        dead_zone_ratio: float = 0.05,
        smoothing_alpha: float = 0.20,
        sample_interval_sec: float = 0.10,
    ) -> list[ReframeKeyframe]:
        """
        Genera la secuencia de ReframeKeyframe para convertir video horizontal a formato vertical 9:16.
        Si el video ya es vertical, aplica passthrough sin reencuadre.

        Rendimiento v2: búsqueda de face center usa bisect (O(log n)) en vez de
        iteración lineal O(n), reduciendo de ~6M a ~60K operaciones en videos de 60s.
        """
        analysis_logger.info(
            f"Calculando Smart Reframing ({source_width}x{source_height} → {target_aspect_ratio}, "
            f"{len(face_tracks)} face tracks, duración: {total_duration:.2f}s)"
        )

        # 1. Caso Video Ya Vertical (9:16) → Passthrough 1:1
        if source_height >= source_width and abs((source_width / source_height) - (9 / 16)) < 0.05:
            analysis_logger.info("El video fuente ya tiene relación de aspecto 9:16. Aplicando passthrough.")
            return [
                ReframeKeyframe(
                    timestamp=0.0,
                    crop_x=0.0,
                    crop_y=0.0,
                    crop_width=1.0,
                    crop_height=1.0,
                    scale=1.0,
                ),
                ReframeKeyframe(
                    timestamp=round(total_duration, 3),
                    crop_x=0.0,
                    crop_y=0.0,
                    crop_width=1.0,
                    crop_height=1.0,
                    scale=1.0,
                ),
            ]

        # 2. Dimensiones de recorte 9:16 normalizadas
        target_w_px = (source_height * 9) / 16.0
        crop_width = round(min(1.0, target_w_px / source_width), 4)
        crop_height = 1.0
        max_crop_x = round(1.0 - crop_width, 4)

        # 3. Pre-computar lookup arrays ordenados por timestamp para bisect O(log n)
        #    En vez de iterar todos los puntos para cada keyframe, usamos búsqueda binaria
        face_timestamps: list[float] = []
        face_centers_x: list[float] = []

        for track in face_tracks:
            for p in track.points:
                face_timestamps.append(p.timestamp)
                face_centers_x.append(p.center_x)

        # Ordenar por timestamp (los tracks ya deberían estar ordenados, pero garantizamos)
        if face_timestamps:
            sorted_pairs = sorted(zip(face_timestamps, face_centers_x))
            face_timestamps, face_centers_x = zip(*sorted_pairs)
            face_timestamps = list(face_timestamps)
            face_centers_x = list(face_centers_x)

        # 4. Pre-computar lookup table de escenas para O(1) por keyframe
        #    Usar lista de inicios de escena para bisect
        scene_starts: list[float] = []
        if scenes:
            scene_starts = [sc.start for sc in scenes]

        keyframes: list[ReframeKeyframe] = []

        # Inicializar crop_x centrado en el sujeto inicial (o centro 0.5)
        initial_center_x = cls._get_face_center_bisect(face_timestamps, face_centers_x, 0.0) or 0.5
        current_crop_x = max(0.0, min(max_crop_x, initial_center_x - (crop_width / 2.0)))

        last_scene_idx = -1
        current_time = 0.0

        while current_time <= total_duration:
            t = round(current_time, 3)

            # Buscar escena activa con bisect (O(log n))
            active_scene_idx = 0
            if scene_starts:
                idx = bisect.bisect_right(scene_starts, t) - 1
                active_scene_idx = max(0, idx)

            is_scene_cut = (active_scene_idx != last_scene_idx and last_scene_idx != -1)
            last_scene_idx = active_scene_idx

            # Buscar face center con bisect O(log n)
            face_center_x = cls._get_face_center_bisect(face_timestamps, face_centers_x, t)
            target_center_x = face_center_x if face_center_x is not None else 0.5

            # Posición ideal para centrar al sujeto
            ideal_crop_x = max(0.0, min(max_crop_x, target_center_x - (crop_width / 2.0)))

            if is_scene_cut:
                # Salto instantáneo en corte de plano sin interpolar (§25)
                current_crop_x = ideal_crop_x
            else:
                # Zona muerta: micro-movimientos de cabeza no mueven la cámara
                delta = abs(ideal_crop_x - current_crop_x)
                if delta >= dead_zone_ratio:
                    current_crop_x = (current_crop_x * (1.0 - smoothing_alpha)) + (ideal_crop_x * smoothing_alpha)
                    current_crop_x = max(0.0, min(max_crop_x, current_crop_x))

            keyframes.append(
                ReframeKeyframe(
                    timestamp=t,
                    crop_x=round(current_crop_x, 4),
                    crop_y=0.0,
                    crop_width=crop_width,
                    crop_height=crop_height,
                    scale=1.0,
                )
            )

            current_time += sample_interval_sec

        analysis_logger.info(f"Smart Reframing completado: {len(keyframes)} keyframes generados.")
        return keyframes

    @classmethod
    def _get_face_center_bisect(
        cls,
        timestamps: list[float],
        centers_x: list[float],
        query_time: float,
        max_lookup_window_sec: float = 0.5,
    ) -> float | None:
        """
        Obtiene la coordenada X del rostro activo más cercano al query_time.
        Usa bisect para búsqueda binaria O(log n) en vez de iteración lineal O(n).
        """
        if not timestamps:
            return None

        # Encontrar índice del primer timestamp > query_time
        idx = bisect.bisect_right(timestamps, query_time)

        # Candidato anterior (timestamp <= query_time)
        best_x = None
        best_diff = max_lookup_window_sec

        if idx > 0:
            prev_idx = idx - 1
            diff = query_time - timestamps[prev_idx]
            if diff <= max_lookup_window_sec:
                best_diff = diff
                best_x = centers_x[prev_idx]

        # Candidato siguiente (timestamp > query_time)
        if idx < len(timestamps):
            next_diff = timestamps[idx] - query_time
            if next_diff < best_diff and next_diff <= max_lookup_window_sec:
                best_x = centers_x[idx]

        return best_x
