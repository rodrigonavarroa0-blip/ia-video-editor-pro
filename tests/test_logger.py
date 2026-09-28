"""Tests unitarios para el logger multicanal estructurado."""

from pathlib import Path

from app.core.logger import get_channel_logger


def test_channel_loggers(tmp_path: Path):
    log_dir = tmp_path / "logs"
    app_log = get_channel_logger("app", log_dir=log_dir)
    ffmpeg_log = get_channel_logger("ffmpeg", log_dir=log_dir)

    app_log.info("Mensaje de prueba en app")
    ffmpeg_log.warning("Advertencia de prueba en ffmpeg")

    assert (log_dir / "app.log").exists()
    assert (log_dir / "ffmpeg.log").exists()

    content_app = (log_dir / "app.log").read_text(encoding="utf-8")
    content_ffmpeg = (log_dir / "ffmpeg.log").read_text(encoding="utf-8")

    assert "Mensaje de prueba en app" in content_app
    assert "Advertencia de prueba en ffmpeg" in content_ffmpeg
