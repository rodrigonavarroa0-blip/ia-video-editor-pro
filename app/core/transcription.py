"""Orquestador de transcripción fonética y sincronización para proyectos."""

import json
from collections.abc import Callable
from pathlib import Path

from app.ai.speech_transcriber import SpeechTranscriber
from app.core.logger import ai_logger, emit_ipc_event
from app.core.project import ProjectManager
from app.models.transcript import TranscriptDocument
from app.render.proxy_generator import ProxyGenerator


def transcribe_project(
    project_dir: Path,
    model_size: str | None = None,
    language: str | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> TranscriptDocument:
    """
    Orquesta la transcripción fonética completa de un proyecto:
    1. Localiza o extrae el audio WAV normalizado en cache/audio.wav.
    2. Ejecuta SpeechTranscriber con faster-whisper.
    3. Guarda project/analysis/transcript.json para reproducibilidad (§4.3).
    4. Actualiza project/project.json con las métricas del habla.
    5. Emite evento NDJSON para la UI.
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    audio_file = proj_path / "cache" / "audio.wav"

    # Si audio.wav no existe en cache, intentar extraerlo del primer medio registrado
    if not audio_file.exists() or audio_file.stat().st_size == 0:
        media_files = manifest.get("media_files", [])
        if not media_files:
            # Buscar en raw/
            raw_files = list((proj_path / "raw").glob("*.*"))
            if not raw_files:
                raise FileNotFoundError(f"No se encontraron medios en el proyecto para transcribir: {proj_path}")
            raw_source = raw_files[0]
        else:
            raw_source = Path(media_files[0]["raw_path"])

        ai_logger.info(f"Extrayendo audio para transcripción desde: {raw_source.name}")
        ProxyGenerator.extract_audio_wav(raw_source, audio_file)

    # 2. Ejecutar transcripción
    doc = SpeechTranscriber.transcribe(
        audio_path=audio_file,
        model_size=model_size,
        language=language,
        progress_callback=progress_callback,
    )

    # 3. Guardar analysis/transcript.json
    transcript_dest = proj_path / "analysis" / "transcript.json"
    with open(transcript_dest, "w", encoding="utf-8") as f:
        f.write(doc.model_dump_json(indent=2))

    # 4. Actualizar project.json
    manifest["transcript_ready"] = True
    manifest["language"] = doc.language
    manifest["word_count"] = doc.word_count
    manifest["transcript_path"] = "analysis/transcript.json"

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 5. Emitir evento IPC
    emit_ipc_event(
        "transcription_completed",
        {
            "project_path": str(proj_path),
            "language": doc.language,
            "word_count": doc.word_count,
            "duration_seconds": doc.duration_seconds,
            "segments_count": len(doc.segments),
        },
        progress=1.0,
    )

    return doc
