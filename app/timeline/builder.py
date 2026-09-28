"""Constructor de Timeline Virtual no destructivo inspirado en OpenTimelineIO (§33)."""


from app.core.logger import render_logger
from app.models.editorial import EditAction, EditorialPlan
from app.models.timeline import (
    AudioTrackItem,
    CropCoordinate,
    VideoClipItem,
    VirtualTimeline,
)
from app.models.vision import ReframeKeyframe


class TimelineBuilder:
    """Combina decisiones editoriales, reencuadres y audio en una estructura VirtualTimeline unificada."""

    @classmethod
    def build_timeline(
        cls,
        project_name: str,
        raw_source_path: str,
        editorial_plan: EditorialPlan,
        reframing_keyframes: list[ReframeKeyframe] | None = None,
        master_audio_path: str | None = None,
        fps: float = 30.0,
        width: int = 1080,
        height: int = 1920,
    ) -> VirtualTimeline:
        """
        Construye el VirtualTimeline continuo calculando tiempos y recortes no destructivos.
        """
        render_logger.info(f"Construyendo Virtual Timeline para '{project_name}' ({len(editorial_plan.decisions)} decisiones)")

        video_clips: list[VideoClipItem] = []
        audio_clips: list[AudioTrackItem] = []
        current_timeline_time = 0.0
        clip_counter = 1

        for decision in editorial_plan.decisions:
            # Omitir segmentos descartados (CUT)
            if decision.action == EditAction.CUT:
                continue

            s_in = decision.source_in if decision.source_in is not None else 0.0
            s_out = decision.source_out if decision.source_out is not None else 0.0
            duration = s_out - s_in

            if duration <= 0.01:
                continue

            t_in = round(current_timeline_time, 3)
            t_out = round(t_in + duration, 3)

            # Determinar escala / Punch-in zoom
            scale = 1.15 if decision.action == EditAction.ZOOM_IN else 1.0

            # Determinar recorte y encuadre 9:16 desde reframing keyframes
            crop = cls._get_crop_for_timestamp(s_in, reframing_keyframes, default_scale=scale)

            clip_id = f"v_clip_{clip_counter:03d}"
            video_clips.append(
                VideoClipItem(
                    id=clip_id,
                    source_path=raw_source_path,
                    source_in=s_in,
                    source_out=s_out,
                    timeline_in=t_in,
                    timeline_out=t_out,
                    scale=scale,
                    crop=crop,
                    speed=1.0,
                    volume_db=0.0,
                )
            )

            # Si no hay master de audio único, generar clips de audio sincronizados
            if not master_audio_path:
                audio_clips.append(
                    AudioTrackItem(
                        id=f"a_clip_{clip_counter:03d}",
                        source_path=raw_source_path,
                        source_in=s_in,
                        source_out=s_out,
                        timeline_in=t_in,
                        timeline_out=t_out,
                        volume_db=0.0,
                    )
                )

            current_timeline_time = t_out
            clip_counter += 1

        # Si existe master de audio procesado (-14 LUFS), añadir pista A1 master
        if master_audio_path:
            audio_clips = [
                AudioTrackItem(
                    id="a_master_001",
                    source_path=master_audio_path,
                    source_in=0.0,
                    source_out=round(current_timeline_time, 3),
                    timeline_in=0.0,
                    timeline_out=round(current_timeline_time, 3),
                    volume_db=0.0,
                    is_ducked=False,
                )
            ]

        timeline = VirtualTimeline(
            version=1,
            project_id=project_name,
            fps=fps,
            width=width,
            height=height,
            duration_seconds=round(current_timeline_time, 3),
            video_clips=video_clips,
            audio_clips=audio_clips,
            subtitles=[],
        )

        render_logger.info(
            f"Virtual Timeline generado: {len(video_clips)} clips de video, "
            f"duración final: {timeline.duration_seconds:.2f}s."
        )
        return timeline

    @classmethod
    def _get_crop_for_timestamp(
        cls,
        timestamp: float,
        keyframes: list[ReframeKeyframe] | None,
        default_scale: float = 1.0,
    ) -> CropCoordinate:
        """Busca las coordenadas de recorte más cercanas al timestamp del clip."""
        if not keyframes:
            return CropCoordinate(center_x=0.5, center_y=0.5, scale=default_scale)

        best_kf = keyframes[0]
        best_diff = abs(best_kf.timestamp - timestamp)

        for kf in keyframes:
            diff = abs(kf.timestamp - timestamp)
            if diff < best_diff:
                best_diff = diff
                best_kf = kf

        c_x = best_kf.crop_x + (best_kf.crop_width / 2.0)
        c_y = best_kf.crop_y + (best_kf.crop_height / 2.0)
        return CropCoordinate(center_x=round(c_x, 4), center_y=round(c_y, 4), scale=default_scale)
