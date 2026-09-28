"""Orquestador unificado de análisis audiovisual (§4.3, §13, §14, §15 y §71)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.analyzers.media_probe import MediaProbe
from app.analyzers.scene_detector import SceneDetector
from app.analyzers.silence_detector import SilenceDetector
from app.core.logger import analysis_logger, emit_ipc_event
from app.core.project import ProjectManager
from app.core.transcription import transcribe_project
from app.models.analysis import AnalysisResult
from app.models.media import MediaInfo
from app.models.transcript import TranscriptDocument
from app.render.proxy_generator import ProxyGenerator


def run_full_analysis(
    project_dir: Path,
    progress_callback: Callable[[str, float], None] | None = None,
) -> AnalysisResult:
    """
    Ejecuta el pipeline completo y determinista de análisis audiovisual:
    1. Ingesta y MediaProbe (si no está disponible).
    2. Transcripción fonética palabra por palabra (faster-whisper).
    3. Detección de planos y cortes de cámara (SceneDetector con OpenCV).
    4. Análisis multinivel de pausas y silencios (SilenceDetector con DSP/RMS).
    5. Consolidación en AnalysisResult y serialización de JSONs reproducibles (§4.3).
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    media_files = manifest.get("media_files", [])
    if not media_files:
        raise ValueError(f"El proyecto no contiene archivos de medios ingestados: {proj_path}")

    primary_media = media_files[0]
    raw_path = Path(primary_media["raw_path"])
    proxy_path = Path(primary_media["proxy_path"]) if primary_media.get("proxy_path") else raw_path
    audio_path = Path(primary_media["audio_path"]) if primary_media.get("audio_path") else proj_path / "cache" / "audio.wav"

    analysis_dir = proj_path / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # 1. Media Probe
    if progress_callback:
        progress_callback("media_probe", 0.05)

    media_json_file = analysis_dir / "media.json"
    if media_json_file.exists():
        with open(media_json_file, "r", encoding="utf-8") as f:
            media_info = MediaInfo.model_validate_json(f.read())
    else:
        media_info = MediaProbe.probe(raw_path)
        with open(media_json_file, "w", encoding="utf-8") as f:
            f.write(media_info.model_dump_json(indent=2))

    # 2. Transcripción
    if progress_callback:
        progress_callback("transcription", 0.2)

    transcript_json_file = analysis_dir / "transcript.json"
    if transcript_json_file.exists():
        with open(transcript_json_file, "r", encoding="utf-8") as f:
            transcript = TranscriptDocument.model_validate_json(f.read())
    else:
        transcript = transcribe_project(proj_path)

    # 3. Detección de Escenas (sobre proxy para máxima velocidad)
    if progress_callback:
        progress_callback("scene_detection", 0.5)

    video_for_scenes = proxy_path if proxy_path.exists() else raw_path
    scenes = SceneDetector.detect_scenes(video_for_scenes)
    scenes_json_file = analysis_dir / "scenes.json"
    with open(scenes_json_file, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in scenes], f, indent=2, ensure_ascii=False)

    # 4. Detección de Silencios
    if progress_callback:
        progress_callback("silence_detection", 0.75)

    if not audio_path.exists():
        ProxyGenerator.extract_audio_wav(raw_path, audio_path)

    silence_intervals = SilenceDetector.detect_silence(audio_path)
    silence_json_file = analysis_dir / "silence.json"
    with open(silence_json_file, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in silence_intervals], f, indent=2, ensure_ascii=False)

    # 5. Consolidación de AnalysisResult
    result = AnalysisResult(
        project_id=str(proj_path.name),
        source_media_path=str(raw_path),
        media_info=media_info,
        transcript=transcript,
        silence_intervals=silence_intervals,
        scenes=scenes,
        is_complete=True,
    )

    summary_file = analysis_dir / "analysis_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    # 6. Actualizar project.json
    manifest["analysis_ready"] = True
    manifest["scenes_count"] = len(scenes)
    manifest["silence_intervals_count"] = len(silence_intervals)
    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if progress_callback:
        progress_callback("completed", 1.0)

    emit_ipc_event(
        "analysis_completed",
        {
            "project_path": str(proj_path),
            "scenes_count": len(scenes),
            "silence_intervals_count": len(silence_intervals),
            "word_count": transcript.word_count,
        },
        progress=1.0,
    )

    analysis_logger.info(f"Análisis unificado completado exitosamente para: {proj_path.name}")
    return result
