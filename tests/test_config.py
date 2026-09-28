"""Tests unitarios para el gestor de configuración YAML."""

from app.core.config import ConfigManager


def test_config_loader_default():
    mgr = ConfigManager()
    assert mgr.get("project.format") == "9:16"
    assert mgr.get("audio.target_lufs") == -14.0
    assert mgr.get("ai.model") == "gemini-3.7-flash"
    assert mgr.get("non_existent_key", "default_val") == "default_val"


def test_config_loader_profiles():
    mgr = ConfigManager()
    social_cfg = mgr.get_config_for_profile("social")
    youtube_cfg = mgr.get_config_for_profile("youtube")

    assert social_cfg["project"]["format"] == "9:16"
    assert social_cfg["editorial"]["pacing_mode"] == "fast"

    assert youtube_cfg["project"]["format"] == "16:9"
    assert youtube_cfg["editorial"]["pacing_mode"] == "natural"
