"""Orquestador maestro de renderizado final y conformación a RAW (§4.3 y §99)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.core.logger import emit_ipc_event, render_logger
from app.core.project import ProjectManager
from app.core.timeline import build_and_export_timeline_for_project
from app.models.timeline import VirtualTimeline
from app.render.render_engine import RenderEngine


def render_final_video_for_project(
    project_dir: Path,
    preset: str = "social",
    burn_subtitles: bool = True,
    progress_callback: Callable[[str, float], None] | None = None,
) -> dict:
    """
    Ejecuta el renderizado final de alta calidad conformando a RAW.
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    media_files = manifest.get("media_files", [])
    if not media_files:
        raise FileNotFoundError(f"No hay archivos de medios en el proyecto: {proj_path}")

    raw_path = Path(media_files[0]["raw_path"])

    # 1. Cargar VirtualTimeline
    vt_file = proj_path / "timeline" / "virtual_timeline.json"
    if not vt_file.exists():
        render_logger.info("VirtualTimeline no encontrado, generando automáticamente...")
        build_and_export_timeline_for_project(proj_path)

    with open(vt_file, "r", encoding="utf-8") as f:
        vt_data = json.load(f)
    timeline = VirtualTimeline.model_validate(vt_data)

    # 2. Localizar master de audio
    audio_master_path = proj_path / "cache" / "audio_master.wav"
    if not audio_master_path.exists():
        audio_master_path = proj_path / "cache" / "audio.wav"
    audio_file = audio_master_path if audio_master_path.exists() else None

    # 3. Localizar subtítulos ASS si se solicita quemado
    sub_file = None
    if burn_subtitles:
        sub_ass = proj_path / "renders" / "subtitles.ass"
        if sub_ass.exists():
            sub_file = sub_ass

    renders_dir = proj_path / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    out_final_video = renders_dir / "final_video.mp4"

    if progress_callback:
        progress_callback("rendering_final_video", 0.5)

    # 4. Renderizar con RenderEngine
    metadata = RenderEngine.render_timeline(
        timeline=timeline,
        raw_source_path=raw_path,
        output_file=out_final_video,
        audio_file=audio_file,
        subtitle_file=sub_file,
        preset_name=preset,
    )

    if progress_callback:
        progress_callback("completed", 1.0)

    # 5. Actualizar project.json
    manifest["rendered"] = True
    manifest["final_video_path"] = "renders/final_video.mp4"
    manifest["final_video_size_mb"] = metadata["file_size_mb"]
    manifest["final_video_duration"] = metadata["duration_seconds"]
    manifest["render_preset"] = preset

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    emit_ipc_event(
        "render_completed",
        {
            "project_path": str(proj_path),
            "final_video_path": str(out_final_video),
            "file_size_mb": metadata["file_size_mb"],
            "duration_seconds": metadata["duration_seconds"],
            "preset": preset,
            "sha256": metadata["sha256"],
        },
        progress=1.0,
    )

    render_logger.info(
        f"Exportación final completada para {proj_path.name}: "
        f"{out_final_video.name} ({metadata['file_size_mb']} MB, {metadata['duration_seconds']}s)"
    )
    return metadata
