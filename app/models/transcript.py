"""Modelos de datos para transcripción de audio y sincronización fonética."""


from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Palabra individual con marca de tiempo precisa."""
    word: str
    start: float = Field(..., description="Timestamp de inicio en segundos")
    end: float = Field(..., description="Timestamp de finalización en segundos")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_filler: bool = False
    is_highlight: bool = False
    speaker: str | None = None


class TranscriptSegment(BaseModel):
    """Segmento de frase u oración."""
    id: int
    text: str
    start: float
    end: float
    words: list[WordTimestamp] = Field(default_factory=list)
    confidence: float = 1.0
    speech_rate_wpm: float | None = None
    speaker: str | None = None


class TranscriptDocument(BaseModel):
    """Documento completo de transcripción de un archivo multimedia."""
    language: str = "es"
    duration_seconds: float
    text: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    all_words: list[WordTimestamp] = Field(default_factory=list)
    word_count: int = 0
