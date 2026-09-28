"""Modelo de consolidación de todos los resultados de análisis audiovisual."""


from pydantic import BaseModel, Field

from app.models.audio import AudioMetrics
from app.models.editorial import SceneBoundary, SilenceInterval
from app.models.media import MediaInfo
from app.models.transcript import TranscriptDocument
from app.models.vision import FaceTrack, ReframeKeyframe


class AnalysisResult(BaseModel):
    """Contenedor maestro que agrupa todos los artefactos de análisis generados (§4.3 y §71)."""
    project_id: str
    source_media_path: str
    media_info: MediaInfo
    transcript: TranscriptDocument | None = None
    silence_intervals: list[SilenceInterval] = Field(default_factory=list)
    scenes: list[SceneBoundary] = Field(default_factory=list)
    audio_metrics: AudioMetrics | None = None
    face_tracks: list[FaceTrack] = Field(default_factory=list)
    reframe_keyframes: list[ReframeKeyframe] = Field(default_factory=list)
    is_complete: bool = False
