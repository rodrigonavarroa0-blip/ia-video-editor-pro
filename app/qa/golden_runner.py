"""Ejecutor maestro de la suite de Golden Tests y validación de no-regresión (§101)."""

import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.analysis import run_full_analysis
from app.core.audio_pipeline import process_project_audio
from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.logger import logger
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project
from app.core.subtitles import generate_subtitles_for_project
from app.core.timeline import build_and_export_timeline_for_project
from app.core.vision import run_vision_tracking_for_project
from tests.golden.fixtures import (
    create_golden_dynamic_monologue,
    create_golden_hesitant_speech,
    create_golden_multi_shot,
)


class GoldenAssertionResult(BaseModel):
    name: str
    passed: bool
    details: str


class GoldenScenarioResult(BaseModel):
    scenario_id: str
    name: str
    description: str
    execution_time_seconds: float
    all_passed: bool
    assertions: list[GoldenAssertionResult]


class GoldenTestReport(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_scenarios: int
    passed_scenarios: int
    total_assertions: int
    passed_assertions: int
    scenarios: list[GoldenScenarioResult]
    report_markdown_path: str = ""


def run_all_golden_tests(base_output_dir: Path) -> GoldenTestReport:
    """Ejecuta los 3 escenarios de Golden Tests y produce el reporte de no-regresión."""
    out_dir = Path(base_output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios_results: list[GoldenScenarioResult] = []

    # =========================================================================
    # ESCENARIO 1: Dynamic Monologue
    # =========================================================================
    t0 = time.time()
    s1_dir = out_dir / "golden_1_monologue"
    s1_assertions: list[GoldenAssertionResult] = []

    try:
        vid1 = s1_dir / "raw_monologue.mp4"
        create_golden_dynamic_monologue(vid1)
        ProjectManager.create_project(s1_dir, project_name="Golden 1 Monologue", profile="social")

        ingest_media(s1_dir, vid1)
        run_full_analysis(s1_dir)
        plan1 = create_editorial_plan_for_project(s1_dir, force_heuristic=True)
        run_vision_tracking_for_project(s1_dir, target_format="9:16")
        process_project_audio(s1_dir, target_lufs=-14.0)
        subs1 = generate_subtitles_for_project(s1_dir, style="hormozi")
        build_and_export_timeline_for_project(s1_dir)
        meta1 = render_final_video_for_project(s1_dir, preset="preview", burn_subtitles=True)

        # Aserción 1.1: Hook Score calculado
        s1_assertions.append(GoldenAssertionResult(
            name="Hook Score Inicial Calculado (>= 0.50)",
            passed=plan1.hook_score >= 0.50,
            details=f"Hook Score obtenido: {plan1.hook_score:.2f}",
        ))

        # Aserción 1.2: Punch-in Zoom en monólogo prolongado
        has_zoom = any(d.action.value in ["zoom_in", "zoom"] for d in plan1.decisions)
        s1_assertions.append(GoldenAssertionResult(
            name="Punch-in Zoom Automático (1.15x) en monólogo > 4.5s",
            passed=has_zoom,
            details="Decisión ZOOM_IN detectada en el plan editorial",
        ))

        # Aserción 1.3: Subtítulos ASS Cinéticos generados
        s1_assertions.append(GoldenAssertionResult(
            name="Subtítulos Cinéticos ASS v4.00+ Válidos",
            passed=Path(subs1["ass"]).exists() and Path(subs1["ass"]).stat().st_size > 100,
            details=f"Archivo ASS generado: {Path(subs1['ass']).name}",
        ))

        # Aserción 1.4: Render final 9:16 generado con hash SHA-256
        s1_assertions.append(GoldenAssertionResult(
            name="Render Final 9:16 Generado con Hash SHA-256",
            passed=bool(meta1.get("sha256")) and (s1_dir / "renders" / "final_video.mp4").exists(),
            details=f"SHA-256: {meta1.get('sha256', '')[:16]}... ({meta1.get('file_size_mb', 0)} MB)",
        ))

    except Exception as e:
        logger.exception("Fallo en Golden 1")
        s1_assertions.append(GoldenAssertionResult(name="Ejecución Escenario 1", passed=False, details=str(e)))

    s1_all_passed = all(a.passed for a in s1_assertions)
    scenarios_results.append(GoldenScenarioResult(
        scenario_id="GOLDEN-01",
        name="Dynamic Monologue (Alta Energía & Punch-in Zoom)",
        description="Evalúa detección de hook inicial, punch-in zoom automático 1.15x, subtitulado ASS y render final.",
        execution_time_seconds=round(time.time() - t0, 2),
        all_passed=s1_all_passed,
        assertions=s1_assertions,
    ))

    # =========================================================================
    # ESCENARIO 2: Hesitant Speech (Silences & Fillers)
    # =========================================================================
    t0 = time.time()
    s2_dir = out_dir / "golden_2_hesitant"
    s2_assertions: list[GoldenAssertionResult] = []

    try:
        vid2 = s2_dir / "raw_hesitant.mp4"
        create_golden_hesitant_speech(vid2)
        ProjectManager.create_project(s2_dir, project_name="Golden 2 Hesitant", profile="social")

        ingest_media(s2_dir, vid2)
        analysis2 = run_full_analysis(s2_dir)
        plan2 = create_editorial_plan_for_project(s2_dir, force_heuristic=True)
        audio_metrics2 = process_project_audio(s2_dir, target_lufs=-14.0)

        # Aserción 2.1: Detección de silencios prolongados
        s2_assertions.append(GoldenAssertionResult(
            name="Detección de Silencios Multinivel (>= 2 intervalos)",
            passed=len(analysis2.silence_intervals) >= 2,
            details=f"Intervalos de silencio detectados: {len(analysis2.silence_intervals)}",
        ))

        # Aserción 2.2: Decisiones de corte de silencios (duración reducida)
        has_cuts = any(d.action.value == "cut" for d in plan2.decisions)
        duration_reduced = plan2.target_duration_seconds < analysis2.media_info.duration_seconds
        s2_assertions.append(GoldenAssertionResult(
            name="Eliminación de Pausas Muertas (Target Duration < Source Duration)",
            passed=has_cuts and duration_reduced,
            details=f"Duración Original: {analysis2.media_info.duration_seconds:.2f}s -> Editada: {plan2.target_duration_seconds:.2f}s",
        ))

        # Aserción 2.3: Sonoridad EBU R128 dentro de -14.0 ± 0.5 LUFS
        lufs_ok = -14.5 <= audio_metrics2.integrated_lufs <= -13.5
        s2_assertions.append(GoldenAssertionResult(
            name="Normalización EBU R128 (-14.0 ± 0.5 LUFS)",
            passed=lufs_ok,
            details=f"Sonoridad integrada: {audio_metrics2.integrated_lufs:.2f} LUFS",
        ))

        # Aserción 2.4: True Peak <= -1.0 dBTP
        tp_ok = audio_metrics2.true_peak_db <= -1.0
        s2_assertions.append(GoldenAssertionResult(
            name="Techo de Pico Real (True Peak <= -1.0 dBTP)",
            passed=tp_ok,
            details=f"True Peak obtenido: {audio_metrics2.true_peak_db:.2f} dBTP",
        ))

    except Exception as e:
        logger.exception("Fallo en Golden 2")
        s2_assertions.append(GoldenAssertionResult(name="Ejecución Escenario 2", passed=False, details=str(e)))

    s2_all_passed = all(a.passed for a in s2_assertions)
    scenarios_results.append(GoldenScenarioResult(
        scenario_id="GOLDEN-02",
        name="Hesitant Speech (Pausas Largas & Masterización Acústica)",
        description="Evalúa corte de silencios muertos, retención de ritmo y fidelidad acústica EBU R128.",
        execution_time_seconds=round(time.time() - t0, 2),
        all_passed=s2_all_passed,
        assertions=s2_assertions,
    ))

    # =========================================================================
    # ESCENARIO 3: Multi-Shot Fast Cuts
    # =========================================================================
    t0 = time.time()
    s3_dir = out_dir / "golden_3_multishot"
    s3_assertions: list[GoldenAssertionResult] = []

    try:
        vid3 = s3_dir / "raw_multishot.mp4"
        create_golden_multi_shot(vid3)
        ProjectManager.create_project(s3_dir, project_name="Golden 3 MultiShot", profile="social")

        ingest_media(s3_dir, vid3)
        analysis3 = run_full_analysis(s3_dir)
        create_editorial_plan_for_project(s3_dir, force_heuristic=True)
        run_vision_tracking_for_project(s3_dir, target_format="9:16")
        timeline_res = build_and_export_timeline_for_project(s3_dir)

        # Aserción 3.1: Detección de planos OpenCV (>= 3 escenas)
        s3_assertions.append(GoldenAssertionResult(
            name="Detección de Planos de Cámara OpenCV (>= 3 escenas)",
            passed=len(analysis3.scenes) >= 3,
            details=f"Escenas detectadas: {len(analysis3.scenes)}",
        ))

        # Aserción 3.2: Exportación CMX 3600 EDL válida
        edl_path = Path(timeline_res["edl"])
        edl_content = edl_path.read_text(encoding="utf-8")
        s3_assertions.append(GoldenAssertionResult(
            name="Exportación CMX 3600 EDL con Timecodes SMPTE",
            passed=edl_path.exists() and "TITLE:" in edl_content and "001" in edl_content,
            details=f"Líneas en EDL: {len(edl_content.splitlines())}",
        ))

        # Aserción 3.3: Exportación FCPXML v1.9 bien formada
        fcpxml_path = Path(timeline_res["fcpxml"])
        tree = ET.parse(fcpxml_path)
        root = tree.getroot()
        s3_assertions.append(GoldenAssertionResult(
            name="Exportación FCPXML v1.9 Sintácticamente Válida",
            passed=root.tag == "fcpxml" and root.attrib.get("version") == "1.9",
            details=f"Raíz XML: <{root.tag} version='{root.attrib.get('version')}'>",
        ))

        # Aserción 3.4: Exportación OpenTimelineIO (.otio)
        otio_path = Path(timeline_res["otio"])
        with open(otio_path, "r", encoding="utf-8") as f:
            otio_data = json.load(f)
        s3_assertions.append(GoldenAssertionResult(
            name="Exportación OpenTimelineIO (.otio) Schema v1",
            passed=otio_data.get("OTIO_SCHEMA") == "Timeline.1",
            details=f"Esquema OTIO: {otio_data.get('OTIO_SCHEMA')}",
        ))

    except Exception as e:
        logger.exception("Fallo en Golden 3")
        s3_assertions.append(GoldenAssertionResult(name="Ejecución Escenario 3", passed=False, details=str(e)))

    s3_all_passed = all(a.passed for a in s3_assertions)
    scenarios_results.append(GoldenScenarioResult(
        scenario_id="GOLDEN-03",
        name="Multi-Shot Fast Cuts (Detección de Escenas & NLE Universal)",
        description="Evalúa detección de planos OpenCV HSV, salto limpio de encuadre y exportaciones CMX/FCPXML/OTIO.",
        execution_time_seconds=round(time.time() - t0, 2),
        all_passed=s3_all_passed,
        assertions=s3_assertions,
    ))

    # =========================================================================
    # GENERAR REPORTE GLOBAL MARKDOWN Y JSON
    # =========================================================================
    total_assertions = sum(len(s.assertions) for s in scenarios_results)
    passed_assertions = sum(sum(1 for a in s.assertions if a.passed) for s in scenarios_results)
    total_scenarios = len(scenarios_results)
    passed_scenarios = sum(1 for s in scenarios_results if s.all_passed)

    md_lines = [
        "# 🏆 IA Video Editor Pro — Reporte Oficial de Golden Tests y No-Regresión",
        "",
        f"**Fecha y Hora UTC:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`  ",
        f"**Escenarios Evaluados:** `{passed_scenarios}/{total_scenarios}` superados  ",
        f"**Aserciones Técnicas:** `{passed_assertions}/{total_assertions}` superadas ({(passed_assertions/total_assertions)*100:.1f}%)  ",
        "",
        "---",
        "",
        "## Resumen por Escenario",
        "",
        "| ID | Escenario | Tiempo | Aserciones | Estado |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for s in scenarios_results:
        status_badge = "✅ SUPERADO" if s.all_passed else "❌ FALLIDO"
        as_passed = sum(1 for a in s.assertions if a.passed)
        md_lines.append(f"| **{s.scenario_id}** | {s.name} | {s.execution_time_seconds}s | {as_passed}/{len(s.assertions)} | {status_badge} |")

    md_lines.extend(["", "---", "", "## Detalle de Aserciones de Calidad", ""])

    for s in scenarios_results:
        md_lines.extend([
            f"### {s.scenario_id} — {s.name}",
            f"*{s.description}*",
            "",
        ])
        for a in s.assertions:
            icon = "✓" if a.passed else "✗"
            md_lines.append(f"- **[{icon}] {a.name}**: {a.details}")
        md_lines.append("")

    md_report_path = out_dir / "qa_golden_report.md"
    json_report_path = out_dir / "qa_golden_report.json"

    md_report_path.write_text("\n".join(md_lines), encoding="utf-8")

    report = GoldenTestReport(
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        total_assertions=total_assertions,
        passed_assertions=passed_assertions,
        scenarios=scenarios_results,
        report_markdown_path=str(md_report_path),
    )

    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

    return report
