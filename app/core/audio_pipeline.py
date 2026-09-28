"""Orquestador maestro de procesamiento, realce y masterización de audio (§4.3 y §96)."""

import json
from collections.abc import Callable
from pathlib import Path

from app.audio.loudness import LoudnessProcessor
from app.audio.voice_enhancer import VoiceEnhancer
from app.core.logger import emit_ipc_event, render_logger
from app.core.project import ProjectManager
from app.models.audio import AudioMetrics
from app.render.proxy_generator import ProxyGenerator


def process_project_audio(
    project_dir: Path,
    target_lufs: float = -14.0,
    progress_callback: Callable[[str, float], None] | None = None,
) -> AudioMetrics:
    """
    Ejecuta el pipeline completo de masterización de audio:
    1. Medición de sonoridad inicial (EBU R128).
    2. Voice Enhancement (High-Pass 80Hz + EQ paramétrica + compresión).
    3. Normalización estricta a target_lufs (-14.0 LUFS) y techo -1.0 dBTP.
    4. Serialización de analysis/audio_metrics.json y cache/audio_master.wav.
    5. Actualización del manifiesto project.json.
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    cache_dir = proj_path / "cache"
    analysis_dir = proj_path / "analysis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    input_audio = cache_dir / "audio.wav"

    # Si audio.wav no existe, extraerlo del primer medio
    if not input_audio.exists():
        media_files = manifest.get("media_files", [])
        if not media_files:
            raise FileNotFoundError(f"No hay archivos de medios en el proyecto para procesar audio: {proj_path}")
        raw_source = Path(media_files[0]["raw_path"])
        ProxyGenerator.extract_audio_wav(raw_source, input_audio)

    # 1. Medir audio original
    if progress_callback:
        progress_callback("measuring_raw", 0.1)

    raw_metrics = LoudnessProcessor.measure_loudness(input_audio, target_lufs=target_lufs)
    with open(analysis_dir / "audio_metrics_raw.json", "w", encoding="utf-8") as f:
        f.write(raw_metrics.model_dump_json(indent=2))

    # 2. Voice Enhancement (DSP)
    if progress_callback:
        progress_callback("voice_enhancement", 0.4)

    enhanced_wav = cache_dir / "audio_enhanced.wav"
    VoiceEnhancer.enhance_voice_track(input_audio, enhanced_wav)

    # 3. Normalización EBU R128 final
    if progress_callback:
        progress_callback("loudness_normalization", 0.7)

    master_wav = cache_dir / "audio_master.wav"
    _, final_metrics = LoudnessProcessor.normalize_audio(
        enhanced_wav,
        master_wav,
        target_lufs=target_lufs,
        max_true_peak_db=-1.0,
    )

    # 4. Guardar analysis/audio_metrics.json
    with open(analysis_dir / "audio_metrics.json", "w", encoding="utf-8") as f:
        f.write(final_metrics.model_dump_json(indent=2))

    # 5. Actualizar project.json
    manifest["audio_processed"] = True
    manifest["final_lufs"] = final_metrics.integrated_lufs
    manifest["true_peak_db"] = final_metrics.true_peak_db
    manifest["audio_master_path"] = "cache/audio_master.wav"

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if progress_callback:
        progress_callback("completed", 1.0)

    # 6. Emitir evento IPC
    emit_ipc_event(
        "audio_processing_completed",
        {
            "project_path": str(proj_path),
            "integrated_lufs": final_metrics.integrated_lufs,
            "true_peak_db": final_metrics.true_peak_db,
            "lra_lu": final_metrics.lra_lu,
            "gain_applied_db": final_metrics.gain_adjustment_db,
        },
        progress=1.0,
    )

    render_logger.info(
        f"Masterización de audio completada para {proj_path.name}: "
        f"{final_metrics.integrated_lufs:.1f} LUFS, True Peak: {final_metrics.true_peak_db:.1f} dBTP."
    )
    return final_metrics
