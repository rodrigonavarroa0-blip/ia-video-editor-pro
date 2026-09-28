"""Tests unitarios para el motor de seguimiento facial (FaceTracker)."""

from pathlib import Path

from app.vision.face_tracker import FaceTracker


def test_face_tracker_synthetic(synthetic_video: Path):
    """Ejecuta FaceTracker sobre video sintético verificando estructura y límites."""
    tracks = FaceTracker.track_faces(synthetic_video, sample_step=1)

    assert isinstance(tracks, list)
    for t in tracks:
        assert t.track_id > 0
        assert 0.0 <= t.average_confidence <= 1.0
        for p in t.points:
            assert p.timestamp >= 0.0
            assert 0.0 <= p.bbox.x_min <= 1.0
            assert 0.0 <= p.bbox.y_min <= 1.0
            assert 0.0 <= p.bbox.width <= 1.0
            assert 0.0 <= p.bbox.height <= 1.0
