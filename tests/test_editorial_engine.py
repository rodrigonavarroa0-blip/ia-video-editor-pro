"""Tests unitarios para la fachada EditorialEngine y GeminiClient."""

from app.ai.editorial_engine import EditorialEngine
from app.ai.gemini_client import GeminiEditorialClient
from app.models.analysis import AnalysisResult
from app.models.media import MediaInfo


def test_gemini_client_availability_check():
    # is_available retorna bool limpiamente
    available = GeminiEditorialClient.is_available()
    assert isinstance(available, bool)


def test_editorial_engine_force_heuristic():
    media = MediaInfo(
        file_path="/tmp/test.mp4", file_name="test.mp4", file_size_bytes=1000,
        format_name="mp4", duration_seconds=3.0, video_streams=[], audio_streams=[]
    )
    analysis = AnalysisResult(
        project_id="engine_test", source_media_path="/tmp/test.mp4",
        media_info=media, transcript=None, silence_intervals=[], scenes=[], is_complete=True
    )

    plan = EditorialEngine.generate_plan(analysis, target_profile="social", force_heuristic=True)
    assert plan is not None
    assert plan.project_id == "engine_test"
    assert len(plan.decisions) >= 1
