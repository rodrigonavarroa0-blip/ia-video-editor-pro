"""Tests unitarios para los modelos de datos Pydantic de IA Video Editor Pro."""

from app.models.analysis import AnalysisResult
from app.models.audio import AudioMetrics
from app.models.editorial import (
    ActionType,
    EditDecision,
    EditorialPlan,
    SilenceInterval,
    SilenceSeverity,
)
from app.models.media import AudioStreamInfo, MediaInfo, VideoStreamInfo
from app.models.timeline import (
    CropCoordinate,
    SubtitleItem,
    VideoClipItem,
    VirtualTimeline,
)
from app.models.transcript import TranscriptDocument, TranscriptSegment, WordTimestamp
from app.models.vision import BoundingBox, FaceTrack, FaceTrackPoint, ReframeKeyframe


def test_media_info_model():
    video_stream = VideoStreamInfo(
        codec_name="hevc",
        width=3840,
        height=2160,
        fps=30.0,
        duration_seconds=120.5,
    )
    audio_stream = AudioStreamInfo(
        codec_name="aac",
        sample_rate=48000,
        channels=2,
        duration_seconds=120.5,
    )
    media = MediaInfo(
        file_path="/videos/raw1.mp4",
        file_name="raw1.mp4",
        file_size_bytes=1024000,
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        duration_seconds=120.5,
        video_streams=[video_stream],
        audio_streams=[audio_stream],
    )

    assert media.primary_video is not None
    assert media.primary_video.width == 3840
    assert media.primary_audio is not None
    assert media.primary_audio.sample_rate == 48000
    assert media.has_video is True


def test_transcript_models():
    w1 = WordTimestamp(word="Hola", start=0.0, end=0.4, confidence=0.98)
    w2 = WordTimestamp(word="mundo", start=0.5, end=0.9, confidence=0.99, is_highlight=True)
    seg = TranscriptSegment(id=1, text="Hola mundo", start=0.0, end=0.9, words=[w1, w2])
    doc = TranscriptDocument(
        language="es",
        duration_seconds=1.0,
        text="Hola mundo",
        segments=[seg],
        all_words=[w1, w2],
        word_count=2,
    )

    assert doc.word_count == 2
    assert doc.segments[0].words[1].is_highlight is True


def test_editorial_models():
    silence = SilenceInterval(
        start=2.0,
        end=3.2,
        duration=1.2,
        severity=SilenceSeverity.CUT_AGGRESSIVE,
    )
    decision = EditDecision(
        id=1,
        start=2.0,
        end=3.2,
        action=ActionType.CUT,
        reason="Silencio largo mayor a 1.0s",
        confidence=0.95,
    )
    plan = EditorialPlan(
        project_id="proj-123",
        source_media_path="/videos/source.mp4",
        source_duration_seconds=60.0,
        decisions=[decision],
        estimated_final_duration_seconds=58.8,
        total_cuts_count=1,
    )

    assert silence.duration == 1.2
    assert plan.total_cuts_count == 1
    assert plan.decisions[0].action == ActionType.CUT


def test_virtual_timeline_model():
    clip = VideoClipItem(
        id="c1",
        source_path="/videos/raw.mp4",
        source_in=0.0,
        source_out=10.0,
        timeline_in=0.0,
        timeline_out=10.0,
        crop=CropCoordinate(center_x=0.5, center_y=0.5, scale=1.0),
    )
    sub = SubtitleItem(id="s1", text="Bienvenidos", start=0.5, end=2.0)
    timeline = VirtualTimeline(
        project_id="proj-123",
        fps=30.0,
        width=1080,
        height=1920,
        duration_seconds=10.0,
        video_clips=[clip],
        subtitles=[sub],
    )

    assert len(timeline.video_clips) == 1
    assert timeline.video_clips[0].source_out == 10.0
    assert timeline.subtitles[0].text == "Bienvenidos"


def test_audio_and_vision_models():
    audio_metrics = AudioMetrics(
        integrated_lufs=-14.2,
        true_peak_db=-1.1,
        speech_energy_ratio=0.85,
    )
    assert audio_metrics.integrated_lufs == -14.2

    bbox = BoundingBox(x_min=0.2, y_min=0.1, width=0.3, height=0.4)
    point = FaceTrackPoint(timestamp=1.5, bbox=bbox, center_x=0.35, center_y=0.3)
    track = FaceTrack(track_id=1, points=[point])
    assert len(track.points) == 1

    keyframe = ReframeKeyframe(timestamp=1.5, crop_x=0.35, crop_y=0.5, crop_width=0.5625, crop_height=1.0)
    assert keyframe.crop_x == 0.35


def test_analysis_result_aggregation():
    media = MediaInfo(
        file_path="/videos/raw.mp4",
        file_name="raw.mp4",
        file_size_bytes=1000,
        format_name="mp4",
        duration_seconds=10.0,
    )
    analysis = AnalysisResult(
        project_id="p-100",
        source_media_path="/videos/raw.mp4",
        media_info=media,
        is_complete=True,
    )
    assert analysis.is_complete is True
    assert analysis.media_info.duration_seconds == 10.0
