"""Gestor de proyectos y directorios no destructivos para IA Video Editor Pro."""

import json
from pathlib import Path
from typing import Any

from app.core.config import config
from app.core.logger import logger


class ProjectManager:
    """Administra la creación, estructura de carpetas y persistencia del proyecto."""

    REQUIRED_FOLDERS = [
        "raw",
        "cache",
        "analysis",
        "proxies",
        "timeline",
        "assets/sfx",
        "assets/music",
        "assets/broll",
        "assets/luts",
        "renders",
        "logs",
    ]

    @classmethod
    def create_project(
        cls,
        project_dir: Path,
        project_name: str = "Nuevo Proyecto",
        profile: str = "social",
    ) -> Path:
        """Crea el árbol de carpetas estándar del proyecto e inicializa project.json."""
        project_path = Path(project_dir).resolve()
        project_path.mkdir(parents=True, exist_ok=True)

        for folder in cls.REQUIRED_FOLDERS:
            (project_path / folder).mkdir(parents=True, exist_ok=True)

        profile_config = config.get_config_for_profile(profile)

        project_manifest: dict[str, Any] = {
            "name": project_name,
            "version": 1,
            "profile": profile,
            "created_at": None,
            "format": profile_config.get("project", {}).get("format", "9:16"),
            "target_resolution": profile_config.get("project", {}).get("target_resolution", {"width": 1080, "height": 1920}),
            "fps": profile_config.get("project", {}).get("fps", 30),
            "media_files": [],
            "analysis_ready": False,
            "timeline_ready": False,
        }

        manifest_file = project_path / "project.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(project_manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"Proyecto '{project_name}' inicializado correctamente en: {project_path}")
        return project_path

    @classmethod
    def load_project(cls, project_dir: Path) -> dict[str, Any]:
        """Carga y valida el archivo project.json."""
        manifest_file = Path(project_dir) / "project.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"No se encontró project.json en {project_dir}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            return json.load(f)
