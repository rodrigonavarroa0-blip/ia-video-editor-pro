"""Orquestador de Ingesta no destructiva de medios audiovisuales."""

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.analyzers.media_probe import MediaProbe
from app.core.logger import emit_ipc_event, logger
from app.core.project import ProjectManager
from app.render.proxy_generator import ProxyGenerator


def ingest_media(
    project_dir: Path,
    source_video_path: Path,
    copy_raw: bool = True,
    generate_proxy: bool = True,
    extract_audio: bool = True,
    progress_callback: Callable[[str, float], None] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta el pipeline completo de ingesta no destructiva:
    1. Inspección técnica de metadatos (MediaProbe).
    2. Copia o vinculación del archivo original a project/raw/.
    3. Serialización de project/analysis/media.json.
    4. Generación de proxy 720p en project/proxies/.
    5. Extracción de audio PCM WAV en project/cache/audio.wav.
    6. Actualización del manifiesto project.json.
    """
    proj_path = Path(project_dir).resolve()
    src_path = Path(source_video_path).resolve()

    if not src_path.exists():
        raise FileNotFoundError(f"Archivo de origen no encontrado: {src_path}")

    # Verificar que el proyecto esté inicializado
    project_manifest = ProjectManager.load_project(proj_path)

    if progress_callback:
        progress_callback("probing", 0.1)

    # 1. MediaProbe
    media_info = MediaProbe.probe(src_path)

    # 2. Guardar en project/raw/
    raw_dest = proj_path / "raw" / src_path.name
    if copy_raw and not raw_dest.exists():
        logger.info(f"Copiando RAW original a: {raw_dest}")
        shutil.copy2(src_path, raw_dest)
    elif not copy_raw and not raw_dest.exists():
        try:
            raw_dest.symlink_to(src_path)
        except OSError:
            shutil.copy2(src_path, raw_dest)

    # 3. Guardar analysis/media.json
    analysis_file = proj_path / "analysis" / "media.json"
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(media_info.model_dump_json(indent=2))

    proxy_path = None
    if generate_proxy and media_info.has_video:
        if progress_callback:
            progress_callback("generating_proxy", 0.3)
        proxy_dest = proj_path / "proxies" / f"proxy_{src_path.stem}.mp4"

        def _proxy_cb(p: float):
            if progress_callback:
                progress_callback("generating_proxy", 0.3 + 0.4 * p)

        ProxyGenerator.generate_proxy(
            source_path=raw_dest if raw_dest.exists() else src_path,
            output_path=proxy_dest,
            media_info=media_info,
            progress_callback=_proxy_cb,
        )
        proxy_path = str(proxy_dest)

    audio_wav_path = None
    if extract_audio and media_info.has_audio:
        if progress_callback:
            progress_callback("extracting_audio", 0.7)
        audio_dest = proj_path / "cache" / "audio.wav"

        def _audio_cb(p: float):
            if progress_callback:
                progress_callback("extracting_audio", 0.7 + 0.3 * p)

        ProxyGenerator.extract_audio_wav(
            source_path=raw_dest if raw_dest.exists() else src_path,
            output_wav_path=audio_dest,
            duration_seconds=media_info.duration_seconds,
            progress_callback=_audio_cb,
        )
        audio_wav_path = str(audio_dest)

    # 6. Actualizar project.json
    media_entry = {
        "file_name": src_path.name,
        "raw_path": str(raw_dest),
        "proxy_path": proxy_path,
        "audio_path": audio_wav_path,
        "duration_seconds": media_info.duration_seconds,
        "width": media_info.primary_video.width if media_info.primary_video else None,
        "height": media_info.primary_video.height if media_info.primary_video else None,
        "fps": media_info.primary_video.fps if media_info.primary_video else None,
    }

    project_manifest["media_files"].append(media_entry)
    manifest_file = proj_path / "project.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(project_manifest, f, indent=2, ensure_ascii=False)

    if progress_callback:
        progress_callback("completed", 1.0)

    emit_ipc_event("media_ingested", media_entry, progress=1.0)
    logger.info(f"Ingesta completada para: {src_path.name}")
    return media_entry
