"""Tests unitarios para el motor de Smart Reframing 9:16."""

from app.models.vision import BoundingBox, FaceTrack, FaceTrackPoint
from app.vision.smart_reframe import SmartReframer


def test_smart_reframe_horizontal_video():
    """Video horizontal 1920x1080 debe generar ventana de recorte 9:16 (~0.3164 normalizado)."""
    keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=1920,
        source_height=1080,
        total_duration=2.0,
        face_tracks=[],
        target_aspect_ratio="9:16",
    )

    assert len(keyframes) >= 2
    first = keyframes[0]
    expected_crop_w = round((1080 * 9) / (1920 * 16), 4)  # 0.3164
    assert abs(first.crop_width - expected_crop_w) < 0.01
    assert first.crop_height == 1.0
    # Al no haber rostros, debe centrar el recorte
    expected_center_x = round((1.0 - expected_crop_w) / 2.0, 4)
    assert abs(first.crop_x - expected_center_x) < 0.02


def test_smart_reframe_vertical_passthrough():
    """Video ya vertical (1080x1920) debe aplicar passthrough 1:1."""
    keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=1080,
        source_height=1920,
        total_duration=3.0,
        face_tracks=[],
        target_aspect_ratio="9:16",
    )

    assert len(keyframes) == 2
    assert keyframes[0].crop_x == 0.0
    assert keyframes[0].crop_width == 1.0
    assert keyframes[0].crop_height == 1.0


def test_smart_reframe_face_following_and_dead_zone():
    """Comprueba que la cámara siga al rostro y aplique Dead Zone."""
    # Rostro a la izquierda (x=0.30)
    p1 = FaceTrackPoint(
        timestamp=0.0,
        bbox=BoundingBox(x_min=0.2, y_min=0.2, width=0.2, height=0.2),
        center_x=0.30,
        center_y=0.30,
    )
    p2 = FaceTrackPoint(
        timestamp=1.0,
        bbox=BoundingBox(x_min=0.6, y_min=0.2, width=0.2, height=0.2),
        center_x=0.70,  # Movimiento hacia la derecha
        center_y=0.30,
    )
    track = FaceTrack(track_id=1, points=[p1, p2])

    keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=1920,
        source_height=1080,
        total_duration=2.0,
        face_tracks=[track],
        target_aspect_ratio="9:16",
        sample_interval_sec=0.5,
    )

    assert len(keyframes) >= 4
    # La posición crop_x debe moverse en dirección al rostro
    assert keyframes[-1].crop_x > keyframes[0].crop_x
