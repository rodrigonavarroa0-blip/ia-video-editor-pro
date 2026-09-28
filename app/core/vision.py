"""Orquestador de seguimiento facial y reencuadre inteligente para proyectos (§4.3 y §95)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.core.logger import analysis_logger, emit_ipc_event
from app.core.project import ProjectManager
from app.models.editorial import SceneBoundary
from app.models.media import MediaInfo
from app.models.vision import FaceTrack, ReframeKeyframe
from app.vision.face_tracker import FaceTracker
from app.vision.smart_reframe import SmartReframer


def run_vision_tracking_for_project(
    project_dir: Path,
    target_format: str = "9:16",
    progress_callback: Callable[[str, float], None] | None = None,
) -> tuple[list[FaceTrack], list[ReframeKeyframe]]:
    """
    Ejecuta el pipeline de visión computacional y reencuadre:
    1. Detección y seguimiento de sujetos con FaceTracker.
    2. Cálculo de keyframes de reencuadre 9:16 con SmartReframer.
    3. Serialización de analysis/face_tracking.json y analysis/reframing.json.
    4. Actualización del manifiesto project.json.
    5. Emisión de eventos IPC.
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    media_files = manifest.get("media_files", [])
    if not media_files:
        raise ValueError(f"El proyecto no contiene archivos de medios ingestados: {proj_path}")

    primary_media = media_files[0]
    raw_path = Path(primary_media["raw_path"])
    proxy_path = Path(primary_media["proxy_path"]) if primary_media.get("proxy_path") else raw_path

    # Video a procesar (preferir proxy para velocidad de FPS)
    video_to_process = proxy_path if proxy_path.exists() else raw_path

    analysis_dir = proj_path / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # 1. Cargar metadatos de media
    media_json_file = analysis_dir / "media.json"
    if media_json_file.exists():
        with open(media_json_file, "r", encoding="utf-8") as f:
            media_info = MediaInfo.model_validate_json(f.read())
    else:
        from app.analyzers.media_probe import MediaProbe
        media_info = MediaProbe.probe(raw_path)

    src_w = media_info.primary_video.width if media_info.primary_video else 1920
    src_h = media_info.primary_video.height if media_info.primary_video else 1080
    total_dur = media_info.duration_seconds

    # 2. Face Tracking
    if progress_callback:
        progress_callback("face_tracking", 0.1)

    def _track_cb(p: float):
        if progress_callback:
            progress_callback("face_tracking", 0.1 + (p * 0.45))

    face_tracks = FaceTracker.track_faces(video_to_process, progress_callback=_track_cb)

    # Guardar analysis/face_tracking.json
    face_json_file = analysis_dir / "face_tracking.json"
    with open(face_json_file, "w", encoding="utf-8") as f:
        json.dump([t.model_dump() for t in face_tracks], f, indent=2, ensure_ascii=False)

    # 3. Cargar escenas para reseteo de cortes
    scenes = []
    scenes_json_file = analysis_dir / "scenes.json"
    if scenes_json_file.exists():
        try:
            with open(scenes_json_file, "r", encoding="utf-8") as f:
                scenes_data = json.load(f)
                scenes = [SceneBoundary.model_validate(s) for s in scenes_data]
        except Exception:
            pass

    # 4. Smart Reframing
    if progress_callback:
        progress_callback("smart_reframing", 0.6)

    reframing_keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=src_w,
        source_height=src_h,
        total_duration=total_dur,
        face_tracks=face_tracks,
        scenes=scenes,
        target_aspect_ratio=target_format,
    )

    # Guardar analysis/reframing.json
    reframe_json_file = analysis_dir / "reframing.json"
    with open(reframe_json_file, "w", encoding="utf-8") as f:
        json.dump([k.model_dump() for k in reframing_keyframes], f, indent=2, ensure_ascii=False)

    # 5. Actualizar project.json
    manifest["vision_tracking_ready"] = True
    manifest["face_tracks_count"] = len(face_tracks)
    manifest["reframing_keyframes_count"] = len(reframing_keyframes)
    manifest["reframing_path"] = "analysis/reframing.json"

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if progress_callback:
        progress_callback("completed", 1.0)

    # 6. Emitir evento IPC
    emit_ipc_event(
        "vision_tracking_completed",
        {
            "project_path": str(proj_path),
            "face_tracks_count": len(face_tracks),
            "reframing_keyframes_count": len(reframing_keyframes),
            "target_format": target_format,
        },
        progress=1.0,
    )

    analysis_logger.info(
        f"Visión y reencuadre completados para {proj_path.name}: "
        f"{len(face_tracks)} tracks, {len(reframing_keyframes)} keyframes 9:16."
    )
    return face_tracks, reframing_keyframes
