"""Motor de transcripción fonética y análisis del habla con faster-whisper."""

import os
import re
import threading
from collections.abc import Callable
from pathlib import Path

from faster_whisper import WhisperModel

from app.core.config import config
from app.core.logger import ai_logger
from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp

# Diccionario configurable de muletillas / filler words por idioma (§20)
DEFAULT_FILLER_WORDS: dict[str, set[str]] = {
    "es": {
        "eh", "este", "bueno", "o sea", "tipo", "um", "ah", "sabes",
        "básicamente", "digamos", "como que", "entonces", "che", "pues",
        "osea", "este...", "mmm", "hmm", "eeh", "aah", "eem"
    },
    "en": {
        "um", "uh", "like", "you know", "basically", "actually",
        "literally", "sort of", "kind of", "i mean", "right", "so",
        "uhh", "umm", "hmm", "well", "okay so", "you see"
    }
}


def clean_word_text(word: str) -> str:
    """Limpia puntuación y caracteres especiales para análisis léxico."""
    return re.sub(r"[^\w\s]", "", word).strip().lower()


def calculate_speech_rate_wpm(word_count: int, duration_seconds: float) -> float:
    """Calcula la tasa de palabras por minuto (Words Per Minute - WPM)."""
    if duration_seconds <= 0 or word_count <= 0:
        return 0.0
    minutes = duration_seconds / 60.0
    return round(word_count / minutes, 1)


class SpeechTranscriber:
    """Transcriptor local de alta precisión con marcas de tiempo a nivel de palabra."""

    _models_cache: dict[str, WhisperModel] = {}
    _cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_model(
        cls,
        model_size: str | None = None,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> WhisperModel:
        """Obtiene o carga en memoria el modelo de Whisper de forma thread-safe."""
        size = model_size or config.get("speech.model", "small")
        cache_key = f"{size}_{device}_{compute_type}"

        with cls._cache_lock:
            if cache_key not in cls._models_cache:
                # Usar todos los núcleos disponibles con fallback a 4
                cpu_threads = int(config.get("speech.cpu_threads", os.cpu_count() or 4))
                ai_logger.info(
                    f"Cargando modelo Whisper local: {size} "
                    f"(device={device}, compute_type={compute_type}, threads={cpu_threads})"
                )
                cls._models_cache[cache_key] = WhisperModel(
                    size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=cpu_threads,
                )

        return cls._models_cache[cache_key]

    @classmethod
    def transcribe(
        cls,
        audio_path: Path,
        model_size: str | None = None,
        language: str | None = None,
        word_timestamps: bool = True,
        filler_words: set[str] | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> TranscriptDocument:
        """
        Transcribe un archivo de audio WAV y genera un TranscriptDocument estructurado
        con timestamps palabra por palabra, detección de muletillas y cálculo de WPM.
        """
        audio_file = Path(audio_path).resolve()
        if not audio_file.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_file}")

        lang = language or config.get("speech.language", "es")
        model = cls.get_model(model_size=model_size)

        fillers = filler_words or DEFAULT_FILLER_WORDS.get(lang, DEFAULT_FILLER_WORDS["es"])

        ai_logger.info(f"Iniciando transcripción de: {audio_file.name} (lang={lang})")

        segments_generator, info = model.transcribe(
            str(audio_file),
            language=lang,
            word_timestamps=word_timestamps,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=250),
        )

        detected_lang = info.language or lang
        total_duration = info.duration or 0.0

        all_words: list[WordTimestamp] = []
        transcript_segments: list[TranscriptSegment] = []
        segment_id = 0

        for seg in segments_generator:
            segment_id += 1
            seg_words: list[WordTimestamp] = []

            if seg.words:
                for w in seg.words:
                    clean = clean_word_text(w.word)
                    is_filler = clean in fillers if clean else False

                    # Validar consistencia de marcas de tiempo
                    start_t = max(0.0, float(w.start))
                    end_t = max(start_t, float(w.end))
                    conf = max(0.0, min(1.0, float(w.probability)))

                    word_obj = WordTimestamp(
                        word=w.word.strip(),
                        start=round(start_t, 3),
                        end=round(end_t, 3),
                        confidence=round(conf, 3),
                        is_filler=is_filler,
                    )
                    seg_words.append(word_obj)
                    all_words.append(word_obj)

            seg_duration = max(0.0, float(seg.end) - float(seg.start))
            seg_wpm = calculate_speech_rate_wpm(len(seg_words), seg_duration)

            transcript_segments.append(
                TranscriptSegment(
                    id=segment_id,
                    text=seg.text.strip(),
                    start=round(float(seg.start), 3),
                    end=round(float(seg.end), 3),
                    words=seg_words,
                    confidence=round(float(getattr(seg, "avg_logprob", 0.0)), 3),
                    speech_rate_wpm=seg_wpm,
                )
            )

            if progress_callback and total_duration > 0:
                p = min(1.0, float(seg.end) / total_duration)
                progress_callback(p)

        full_text = " ".join(s.text for s in transcript_segments)

        doc = TranscriptDocument(
            language=detected_lang,
            duration_seconds=round(total_duration, 3),
            text=full_text,
            segments=transcript_segments,
            all_words=all_words,
            word_count=len(all_words),
        )

        ai_logger.info(
            f"Transcripción completada: {doc.word_count} palabras, "
            f"{len(doc.segments)} segmentos, duración: {doc.duration_seconds:.2f}s"
        )
        return doc
