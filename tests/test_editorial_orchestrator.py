"""Tests de integración para el orquestador editorial."""

from pathlib import Path

from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.project import ProjectManager


def test_create_editorial_plan_orchestrator(synthetic_video: Path, tmp_path: Path):
    proj_dir = tmp_path / "editorial_plan_proj"
    ProjectManager.create_project(proj_dir, project_name="Plan Test", profile="social")

    # Ingestar
    ingest_media(proj_dir, synthetic_video)

    # Crear plan editorial (forzando heurístico offline para consistencia en CI/CD)
    plan = create_editorial_plan_for_project(proj_dir, force_heuristic=True)

    # 1. Verificar archivo en disco
    plan_file = proj_dir / "analysis" / "edit_plan.json"
    assert plan_file.exists()

    # 2. Verificar manifiesto project.json
    manifest = ProjectManager.load_project(proj_dir)
    assert manifest["editorial_plan_ready"] is True
    assert manifest["edit_plan_path"] == "analysis/edit_plan.json"
    assert manifest["decisions_count"] == len(plan.decisions)
