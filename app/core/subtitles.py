"""Orquestador de generación de subtítulos cinéticos y exportación sidecar (§4.3 y §97)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.core.logger import emit_ipc_event, render_logger
from app.core.project import ProjectManager
from app.core.transcription import transcribe_project
from app.models.transcript import TranscriptDocument
from app.subtitles.ass_generator import ASSGenerator
from app.subtitles.burner import SubtitleBurner
from app.subtitles.sidecar_generator import SidecarGenerator


def generate_subtitles_for_project(
    project_dir: Path,
    style: str = "hormozi",
    max_words: int = 3,
    progress_callback: Callable[[str, float], None] | None = None,
) -> dict[str, Path]:
    """
    Orquesta la generación de subtítulos cinéticos (.ass) y formatos universales sidecar (.srt, .vtt).
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    transcript_file = proj_path / "analysis" / "transcript.json"
    if not transcript_file.exists():
        render_logger.info("Transcripción no encontrada, ejecutando transcripción fonética previa...")
        transcribe_project(proj_path)

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)
    transcript_doc = TranscriptDocument.model_validate(transcript_data)

    renders_dir = proj_path / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback("generating_ass", 0.3)

    style_cfg = ASSGenerator.get_style_config(style)
    style_cfg.max_words_per_line = max_words

    ass_path = renders_dir / "subtitles.ass"
    ASSGenerator.generate_ass(transcript_doc, ass_path, style_config=style_cfg)

    if progress_callback:
        progress_callback("generating_sidecar", 0.6)

    srt_path = renders_dir / "subtitles.srt"
    vtt_path = renders_dir / "subtitles.vtt"
    SidecarGenerator.generate_srt(transcript_doc, srt_path, max_words=max_words * 2)
    SidecarGenerator.generate_vtt(transcript_doc, vtt_path, max_words=max_words * 2)

    if progress_callback:
        progress_callback("completed", 1.0)

    # Actualizar project.json
    manifest["subtitles_ready"] = True
    manifest["subtitles_style"] = style
    manifest["subtitles_ass_path"] = "renders/subtitles.ass"
    manifest["subtitles_srt_path"] = "renders/subtitles.srt"
    manifest["subtitles_vtt_path"] = "renders/subtitles.vtt"

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    emit_ipc_event(
        "subtitles_generated",
        {
            "project_path": str(proj_path),
            "style": style,
            "ass_path": str(ass_path),
            "srt_path": str(srt_path),
            "vtt_path": str(vtt_path),
        },
        progress=1.0,
    )

    render_logger.info(f"Subtítulos completados para {proj_path.name} con estilo '{style}'.")
    return {
        "ass": ass_path,
        "srt": srt_path,
        "vtt": vtt_path,
    }


def burn_project_subtitles(
    project_dir: Path,
    style: str = "hormozi",
    output_filename: str = "preview_subtitled.mp4",
) -> Path:
    """Quema los subtítulos cinéticos en el proxy del video para visualización previa rápida."""
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    media_files = manifest.get("media_files", [])
    if not media_files:
        raise FileNotFoundError(f"No hay medios ingestados en el proyecto: {proj_path}")

    proxy_file = proj_path / media_files[0]["proxy_path"]
    if not proxy_file.exists():
        proxy_file = Path(media_files[0]["raw_path"])

    subs_dict = generate_subtitles_for_project(proj_path, style=style)
    out_video = proj_path / "renders" / output_filename

    SubtitleBurner.burn_subtitles(
        input_video=proxy_file,
        subtitle_file=subs_dict["ass"],
        output_video=out_video,
    )
    return out_video
