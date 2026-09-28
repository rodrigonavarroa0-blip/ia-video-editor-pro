"""Orquestador de planificación editorial y generación de edit_plan.json (§4.3 y §94)."""

import json
from pathlib import Path

from app.ai.editorial_engine import EditorialEngine
from app.core.analysis import run_full_analysis
from app.core.logger import ai_logger, emit_ipc_event
from app.core.project import ProjectManager
from app.models.analysis import AnalysisResult
from app.models.editorial import EditorialPlan


def create_editorial_plan_for_project(
    project_dir: Path,
    target_profile: str | None = None,
    force_heuristic: bool = False,
) -> EditorialPlan:
    """
    Orquesta la generación del plan de edición de un proyecto:
    1. Carga o genera el AnalysisResult (analysis/analysis_summary.json).
    2. Invoca EditorialEngine (Gemini 3.7 Flash o Heurística Local).
    3. Serializa project/analysis/edit_plan.json.
    4. Actualiza project/project.json con las métricas narrativas.
    5. Emite evento IPC editorial_plan_generated.
    """
    proj_path = Path(project_dir).resolve()
    manifest = ProjectManager.load_project(proj_path)

    profile = target_profile or manifest.get("profile", "social")
    analysis_file = proj_path / "analysis" / "analysis_summary.json"

    # Si no existe el análisis, ejecutarlo
    if not analysis_file.exists():
        ai_logger.info(f"Análisis no encontrado en {proj_path.name}. Ejecutando análisis completo previo...")
        analysis_result = run_full_analysis(proj_path)
    else:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_result = AnalysisResult.model_validate_json(f.read())

    # Generar plan editorial
    plan = EditorialEngine.generate_plan(
        analysis=analysis_result,
        target_profile=profile,
        force_heuristic=force_heuristic,
    )

    # Guardar analysis/edit_plan.json
    edit_plan_path = proj_path / "analysis" / "edit_plan.json"
    with open(edit_plan_path, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2))

    # Actualizar project.json
    manifest["editorial_plan_ready"] = True
    manifest["edit_plan_path"] = "analysis/edit_plan.json"
    manifest["hook_score"] = plan.hook_score
    manifest["retention_score"] = plan.retention_score
    manifest["redundancy_score"] = plan.redundancy_score
    manifest["target_duration_seconds"] = plan.target_duration_seconds
    manifest["decisions_count"] = len(plan.decisions)

    with open(proj_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Emitir evento IPC
    emit_ipc_event(
        "editorial_plan_generated",
        {
            "project_path": str(proj_path),
            "hook_score": plan.hook_score,
            "retention_score": plan.retention_score,
            "redundancy_score": plan.redundancy_score,
            "decisions_count": len(plan.decisions),
            "target_duration_seconds": plan.target_duration_seconds,
            "summary": plan.summary,
        },
        progress=1.0,
    )

    ai_logger.info(f"Plan editorial generado y guardado en: {edit_plan_path}")
    return plan
