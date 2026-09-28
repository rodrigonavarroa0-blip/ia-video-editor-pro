"""Modelos de datos para el Timeline Virtual no destructivo inspirado en OpenTimelineIO."""

from enum import Enum

from pydantic import BaseModel, Field


class TrackType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    GRAPHICS = "graphics"
    SUBTITLES = "subtitles"


class CropCoordinate(BaseModel):
    """Parámetros de encuadre y recorte normalizados (0.0 a 1.0)."""
    center_x: float = 0.5
    center_y: float = 0.5
    scale: float = 1.0


class VideoClipItem(BaseModel):
    """Clip de video ubicado en el timeline virtual."""
    id: str
    source_path: str
    source_in: float = Field(..., description="Punto de entrada en la fuente (segundos)")
    source_out: float = Field(..., description="Punto de salida en la fuente (segundos)")
    timeline_in: float = Field(..., description="Punto de entrada en el timeline (segundos)")
    timeline_out: float = Field(..., description="Punto de salida en el timeline (segundos)")
    scale: float = 1.0
    crop: CropCoordinate = Field(default_factory=CropCoordinate)
    speed: float = 1.0
    volume_db: float = 0.0


class AudioTrackItem(BaseModel):
    """Elemento de audio (música, SFX o voz procesada)."""
    id: str
    source_path: str
    source_in: float
    source_out: float
    timeline_in: float
    timeline_out: float
    volume_db: float = 0.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    is_ducked: bool = False


class SubtitleItem(BaseModel):
    """Elemento de subtítulo individual en el timeline."""
    id: str
    text: str
    start: float
    end: float
    style_name: str = "bold_pop"
    highlight_words: list[str] = Field(default_factory=list)


class VirtualTimeline(BaseModel):
    """Timeline virtual multipista no destructivo."""
    version: int = 1
    project_id: str
    fps: float = 30.0
    width: int = 1080
    height: int = 1920
    duration_seconds: float = 0.0
    video_clips: list[VideoClipItem] = Field(default_factory=list)
    audio_clips: list[AudioTrackItem] = Field(default_factory=list)
    subtitles: list[SubtitleItem] = Field(default_factory=list)


class ExportPreset(BaseModel):
    """Configuración predefinida de exportación."""
    name: str
    target_format: str = "9:16"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "h264_videotoolbox"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    crf: int = 20
