"""Suite de pruebas automatizadas para los Golden Tests (§101)."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app
from app.qa.golden_runner import run_all_golden_tests

runner = CliRunner()


def test_golden_all_scenarios_runner(tmp_path: Path):
    """Ejecuta los 3 escenarios oficiales de Golden Tests y valida 100% de aserciones."""
    report = run_all_golden_tests(tmp_path / "golden_output")

    failed_assertions = []
    for s in report.scenarios:
        for a in s.assertions:
            if not a.passed:
                failed_assertions.append(f"[{s.scenario_id}] {a.name}: {a.details}")

    assert not failed_assertions, f"Fallaron las siguientes aserciones: {failed_assertions}"
    assert report.total_scenarios == 3
    assert report.passed_scenarios == 3
    assert report.total_assertions >= 12
    assert report.passed_assertions == report.total_assertions
    assert Path(report.report_markdown_path).exists()
    assert (tmp_path / "golden_output" / "qa_golden_report.json").exists()


def test_golden_cli_command(tmp_path: Path):
    """Prueba la ejecución de Golden Tests a través del comando CLI iva golden-test."""
    out_dir = str(tmp_path / "cli_golden")
    res = runner.invoke(app, ["golden-test", "--output-dir", out_dir])
    assert res.exit_code == 0
    assert "Reporte de Golden Tests" in res.stdout
    assert "GOLDEN-01" in res.stdout
    assert "GOLDEN-02" in res.stdout
    assert "GOLDEN-03" in res.stdout
