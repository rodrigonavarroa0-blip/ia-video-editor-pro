"""Modelos de datos Pydantic v2 para IA Video Editor Pro."""

from app.models.analysis import AnalysisResult
from app.models.audio import AudioMetrics
from app.models.editorial import (
    EditAction,
    EditDecision,
    EditorialPlan,
    SceneBoundary,
    SilenceInterval,
)
from app.models.media import AudioStreamInfo, MediaInfo, VideoStreamInfo
from app.models.subtitles import SubtitlePreset, SubtitleStyleConfig
from app.models.timeline import (
    AudioTrackItem,
    CropCoordinate,
    ExportPreset,
    SubtitleItem,
    TrackType,
    VideoClipItem,
    VirtualTimeline,
)
from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.models.vision import BoundingBox, FaceTrack, FaceTrackPoint, ReframeKeyframe

__all__ = [
    "AnalysisResult",
    "AudioMetrics",
    "AudioStreamInfo",
    "AudioTrackItem",
    "BoundingBox",
    "CropCoordinate",
    "EditAction",
    "EditDecision",
    "EditorialPlan",
    "ExportPreset",
    "FaceTrack",
    "FaceTrackPoint",
    "MediaInfo",
    "ReframeKeyframe",
    "SceneBoundary",
    "SilenceInterval",
    "SubtitleItem",
    "SubtitlePreset",
    "SubtitleStyleConfig",
    "TrackType",
    "TranscriptDocument",
    "TranscriptSegment",
    "VideoClipItem",
    "VideoStreamInfo",
    "VirtualTimeline",
    "WordTimestamp",
]
