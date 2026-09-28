"""Orquestador de construcción y exportación de timelines e intercambio NLE (§4.3 y §98)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.core.editorial import create_editorial_plan_for_project
from app.core.logger import emit_ipc_event, render_logger
from app.core.project import ProjectManager
from app.models.editorial import EditorialPlan
from app.models.vision import ReframeKeyframe
from app.timeline.builder import TimelineBuilder
from app.timeline.edl_exporter import EDLExporter
from app.timeline.fcpxml_exporter import FCPXMLExporter
from app.timeline.otio_exporter import OTIOExporter


def build_and_export_timeline_for_project(
    project_dir: Path,
    fps: float = 30.0,
    width: int = 1080,
    height: int = 1920,
    progress_callback: Callable[[str, float], None] | None = None,
) -> dict[str, Path]:
    """
    Construye el VirtualTimeline y exporta los archivos de intercambio para NLEs:
    - timeline/virtual_timeline.json
    - timeline/export.edl (CMX 3600)
    - timeline/export.fcpxml (Final Cut Pro / DaVinci Resolve)
    - timeline/export.otio (OpenTimelineIO)
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    media_files = manifest.get("media_files", [])
    if not media_files:
        raise FileNotFoundError(f"No hay archivos de medios en el proyecto: {proj_path}")

    raw_path = str(Path(media_files[0]["raw_path"]))

    # 1. Cargar plan editorial
    edit_plan_file = proj_path / "analysis" / "edit_plan.json"
    if not edit_plan_file.exists():
        render_logger.info("Plan editorial no encontrado, generando automáticamente...")
        editorial_plan = create_editorial_plan_for_project(proj_path, force_heuristic=True)
    else:
        with open(edit_plan_file, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        editorial_plan = EditorialPlan.model_validate(plan_data)

    # 2. Cargar keyframes de reencuadre 9:16 si existen
    reframing_file = proj_path / "analysis" / "reframing.json"
    reframing_keyframes: list[ReframeKeyframe] | None = None
    if reframing_file.exists():
        with open(reframing_file, "r", encoding="utf-8") as f:
            kf_data = json.load(f)
        reframing_keyframes = [ReframeKeyframe.model_validate(k) for k in kf_data]

    # 3. Audio master si está disponible
    master_audio_file = proj_path / "cache" / "audio_master.wav"
    audio_path = str(master_audio_file) if master_audio_file.exists() else None

    if progress_callback:
        progress_callback("building_virtual_timeline", 0.2)

    # 4. Construir VirtualTimeline
    timeline = TimelineBuilder.build_timeline(
        project_name=manifest.get("name", "IVA Project"),
        raw_source_path=raw_path,
        editorial_plan=editorial_plan,
        reframing_keyframes=reframing_keyframes,
        master_audio_path=audio_path,
        fps=fps,
        width=width,
        height=height,
    )

    timeline_dir = proj_path / "timeline"
    timeline_dir.mkdir(parents=True, exist_ok=True)

    # Guardar virtual_timeline.json
    vt_json_path = timeline_dir / "virtual_timeline.json"
    with open(vt_json_path, "w", encoding="utf-8") as f:
        f.write(timeline.model_dump_json(indent=2))

    if progress_callback:
        progress_callback("exporting_edl", 0.4)

    # 5. Exportar CMX 3600 EDL
    edl_path = timeline_dir / "export.edl"
    EDLExporter.export_cmx3600(timeline, edl_path)

    if progress_callback:
        progress_callback("exporting_fcpxml", 0.7)

    # 6. Exportar FCPXML
    fcpxml_path = timeline_dir / "export.fcpxml"
    FCPXMLExporter.export_fcpxml(timeline, fcpxml_path)

    if progress_callback:
        progress_callback("exporting_otio", 0.9)

    # 7. Exportar OpenTimelineIO
    otio_path = timeline_dir / "export.otio"
    OTIOExporter.export_otio(timeline, otio_path)

    if progress_callback:
        progress_callback("completed", 1.0)

    # 8. Actualizar project.json
    manifest["timeline_ready"] = True
    manifest["virtual_timeline_path"] = "timeline/virtual_timeline.json"
    manifest["edl_export_path"] = "timeline/export.edl"
    manifest["fcpxml_export_path"] = "timeline/export.fcpxml"
    manifest["otio_export_path"] = "timeline/export.otio"
    manifest["timeline_duration_seconds"] = timeline.duration_seconds
    manifest["timeline_clips_count"] = len(timeline.video_clips)

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    emit_ipc_event(
        "timeline_generated",
        {
            "project_path": str(proj_path),
            "clips_count": len(timeline.video_clips),
            "duration_seconds": timeline.duration_seconds,
            "edl_path": str(edl_path),
            "fcpxml_path": str(fcpxml_path),
            "otio_path": str(otio_path),
        },
        progress=1.0,
    )

    render_logger.info(f"Integración de Timeline completada para {proj_path.name}: 4 formatos exportados.")
    return {
        "virtual_timeline": vt_json_path,
        "edl": edl_path,
        "fcpxml": fcpxml_path,
        "otio": otio_path,
    }
