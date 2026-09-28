"""Generador de subtítulos sidecar estándar (SRT y WebVTT) (§32)."""

from pathlib import Path

from app.core.logger import render_logger
from app.models.transcript import TranscriptDocument, WordTimestamp


class SidecarGenerator:
    """Genera subtítulos estándar SubRip (.srt) y WebVTT (.vtt) para compatibilidad universal."""

    @classmethod
    def format_srt_timestamp(cls, seconds: float) -> str:
        """Convierte segundos a formato SRT HH:MM:SS,mmm."""
        sec = max(0.0, float(seconds))
        hours = int(sec // 3600)
        minutes = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = round((sec - int(sec)) * 1000)
        if millis >= 1000:
            millis = 999
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @classmethod
    def format_vtt_timestamp(cls, seconds: float) -> str:
        """Convierte segundos a formato WebVTT HH:MM:SS.mmm."""
        sec = max(0.0, float(seconds))
        hours = int(sec // 3600)
        minutes = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = round((sec - int(sec)) * 1000)
        if millis >= 1000:
            millis = 999
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @classmethod
    def generate_srt(
        cls,
        transcript: TranscriptDocument,
        output_file: Path,
        max_words: int = 6,
    ) -> Path:
        """Genera un archivo SubRip .srt estándar."""
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        all_words = cls._extract_words(transcript)
        chunks = cls._group_words(all_words, max_words=max_words)

        srt_blocks = []
        for idx, chunk in enumerate(chunks, 1):
            if not chunk:
                continue
            start_ts = cls.format_srt_timestamp(chunk[0].start)
            end_ts = cls.format_srt_timestamp(chunk[-1].end)
            text = " ".join(w.word.strip() for w in chunk)
            srt_blocks.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_blocks))

        render_logger.info(f"Subtítulos SRT generados: {out_path.name} ({len(chunks)} subtítulos)")
        return out_path

    @classmethod
    def generate_vtt(
        cls,
        transcript: TranscriptDocument,
        output_file: Path,
        max_words: int = 6,
    ) -> Path:
        """Genera un archivo WebVTT .vtt estándar."""
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        all_words = cls._extract_words(transcript)
        chunks = cls._group_words(all_words, max_words=max_words)

        vtt_lines = ["WEBVTT", ""]
        for idx, chunk in enumerate(chunks, 1):
            if not chunk:
                continue
            start_ts = cls.format_vtt_timestamp(chunk[0].start)
            end_ts = cls.format_vtt_timestamp(chunk[-1].end)
            text = " ".join(w.word.strip() for w in chunk)
            vtt_lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(vtt_lines))

        render_logger.info(f"Subtítulos WebVTT generados: {out_path.name} ({len(chunks)} subtítulos)")
        return out_path

    @classmethod
    def _extract_words(cls, transcript: TranscriptDocument) -> list[WordTimestamp]:
        """Obtiene la lista plana de palabras de la transcripción."""
        if transcript.all_words:
            return transcript.all_words
        words = []
        for seg in transcript.segments:
            words.extend(seg.words)
        return words

    @classmethod
    def _group_words(
        cls,
        words: list[WordTimestamp],
        max_words: int = 6,
        max_duration: float = 3.0,
    ) -> list[list[WordTimestamp]]:
        """Agrupa palabras en bloques de subtítulo respetando límites de palabras y duración."""
        chunks: list[list[WordTimestamp]] = []
        current_chunk: list[WordTimestamp] = []

        for word in words:
            if not current_chunk:
                current_chunk.append(word)
                continue

            chunk_duration = word.end - current_chunk[0].start
            chunk_length = len(current_chunk)

            if chunk_length >= max_words or chunk_duration >= max_duration:
                chunks.append(current_chunk)
                current_chunk = [word]
            else:
                current_chunk.append(word)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
