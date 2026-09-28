"""Modelos de datos para análisis e inspección de medios audiovisuales."""


from pydantic import BaseModel, Field


class VideoStreamInfo(BaseModel):
    """Información técnica de un stream de video."""
    index: int = 0
    codec_name: str
    width: int
    height: int
    aspect_ratio: str = "16:9"
    fps: float
    duration_seconds: float
    total_frames: int | None = None
    bitrate_kbps: int | None = None
    pixel_format: str | None = None
    color_space: str | None = None


class AudioStreamInfo(BaseModel):
    """Información técnica de un stream de audio."""
    index: int = 1
    codec_name: str
    sample_rate: int = 44100
    channels: int = 2
    bitrate_kbps: int | None = None
    duration_seconds: float


class MediaInfo(BaseModel):
    """Metadatos completos de un archivo multimedia."""
    file_path: str
    file_name: str
    file_size_bytes: int
    format_name: str
    duration_seconds: float
    video_streams: list[VideoStreamInfo] = Field(default_factory=list)
    audio_streams: list[AudioStreamInfo] = Field(default_factory=list)
    has_video: bool = True
    has_audio: bool = True

    @property
    def primary_video(self) -> VideoStreamInfo | None:
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio(self) -> AudioStreamInfo | None:
        return self.audio_streams[0] if self.audio_streams else None
