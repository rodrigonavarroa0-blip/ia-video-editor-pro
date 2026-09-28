"""Tests unitarios para la creación y gestión de proyectos."""

from pathlib import Path

from app.core.project import ProjectManager


def test_project_creation(tmp_path: Path):
    target_dir = tmp_path / "test_proj"
    created_path = ProjectManager.create_project(
        project_dir=target_dir,
        project_name="Proyecto Test",
        profile="social",
    )

    assert created_path.exists()
    assert (created_path / "raw").is_dir()
    assert (created_path / "proxies").is_dir()
    assert (created_path / "analysis").is_dir()
    assert (created_path / "timeline").is_dir()
    assert (created_path / "assets" / "sfx").is_dir()
    assert (created_path / "assets" / "music").is_dir()
    assert (created_path / "project.json").is_file()

    loaded = ProjectManager.load_project(created_path)
    assert loaded["name"] == "Proyecto Test"
    assert loaded["profile"] == "social"
    assert loaded["format"] == "9:16"
