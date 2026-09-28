"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 5 (§107)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app
from app.models.editorial import SceneBoundary
from app.models.vision import BoundingBox, FaceTrack, FaceTrackPoint
from app.vision.smart_reframe import SmartReframer

runner = CliRunner()


def test_qa_no_faces_center_crop_fallback():
    """Prueba que un video sin rostros mantenga un Center Crop exacto y estable."""
    keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=1920,
        source_height=1080,
        total_duration=5.0,
        face_tracks=[],
        target_aspect_ratio="9:16",
    )

    expected_crop_w = round((1080 * 9) / (1920 * 16), 4)  # 0.3164
    expected_x = round((1.0 - expected_crop_w) / 2.0, 4)  # 0.3418

    for k in keyframes:
        assert abs(k.crop_x - expected_x) < 0.001
        assert abs(k.crop_width - expected_crop_w) < 0.001


def test_qa_scene_cut_smoothing_reset():
    """Comprueba que en un corte de plano la cámara salte de inmediato al sujeto sin interpolar entre planos."""
    # Plano 1: Sujeto a la izquierda (x=0.20) en t=0.0, 1.0, 1.8
    p1 = FaceTrackPoint(timestamp=0.0, bbox=BoundingBox(x_min=0.1, y_min=0.1, width=0.2, height=0.2), center_x=0.20, center_y=0.20)
    p2 = FaceTrackPoint(timestamp=1.0, bbox=BoundingBox(x_min=0.1, y_min=0.1, width=0.2, height=0.2), center_x=0.20, center_y=0.20)
    p3 = FaceTrackPoint(timestamp=1.8, bbox=BoundingBox(x_min=0.1, y_min=0.1, width=0.2, height=0.2), center_x=0.20, center_y=0.20)

    # Plano 2: Sujeto a la derecha (x=0.80) desde t=2.0
    p4 = FaceTrackPoint(timestamp=2.0, bbox=BoundingBox(x_min=0.7, y_min=0.1, width=0.2, height=0.2), center_x=0.80, center_y=0.20)
    p5 = FaceTrackPoint(timestamp=3.0, bbox=BoundingBox(x_min=0.7, y_min=0.1, width=0.2, height=0.2), center_x=0.80, center_y=0.20)

    track1 = FaceTrack(track_id=1, points=[p1, p2, p3])
    track2 = FaceTrack(track_id=2, points=[p4, p5])

    scenes = [
        SceneBoundary(start=0.0, end=2.0, duration=2.0, score=1.0),
        SceneBoundary(start=2.0, end=4.0, duration=2.0, score=1.0),
    ]

    keyframes = SmartReframer.calculate_reframing_keyframes(
        source_width=1920,
        source_height=1080,
        total_duration=4.0,
        face_tracks=[track1, track2],
        scenes=scenes,
        sample_interval_sec=0.2,
        smoothing_alpha=0.05,  # Suavizado extremadamente lento
    )

    # En t=1.8 (antes del corte) y t=2.0 (en el corte)
    kf_before_cut = next(k for k in keyframes if abs(k.timestamp - 1.8) < 0.05)
    kf_at_cut = next(k for k in keyframes if abs(k.timestamp - 2.0) < 0.05)

    # En t=2.0 debe haber un salto drástico hacia la derecha
    assert kf_at_cut.crop_x > kf_before_cut.crop_x + 0.30


def test_qa_cli_vision_commands(synthetic_video: Path, tmp_path: Path):
    """Prueba la ejecución de los comandos CLI track-faces y reframe."""
    # 1. iva track-faces
    res_track = runner.invoke(app, ["track-faces", str(synthetic_video)])
    assert res_track.exit_code == 0
    assert "Face Tracking" in res_track.stdout

    # 2. Ingestar y reencuadrar
    proj_dir = str(tmp_path / "cli_vision_proj")
    runner.invoke(app, ["init-project", proj_dir])
    runner.invoke(app, ["ingest", proj_dir, str(synthetic_video)])

    res_reframe = runner.invoke(app, ["reframe", proj_dir, "--format", "9:16"])
    assert res_reframe.exit_code == 0
    assert "Smart Reframing Completado Exitosamente" in res_reframe.stdout
