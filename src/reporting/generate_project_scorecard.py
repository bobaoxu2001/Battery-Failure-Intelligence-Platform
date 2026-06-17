"""Generate an evidence-based portfolio readiness scorecard.

This report is intentionally blunt: it maps the target Battery Engineering Data
Scientist contractor requirements to concrete repo artifacts. A row passes only
when every listed artifact exists, so the final score is tied to the current
worktree rather than README claims.

Run as a module::

    python -m src.reporting.generate_project_scorecard
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ScorecardItem:
    competency: str
    evidence: tuple[Path, ...]
    note: str


ITEMS = [
    ScorecardItem(
        "Python ML functions",
        (
            config.ROOT / "src/models/train_soh_model.py",
            config.ROOT / "src/models/train_rul_model.py",
            config.ROOT / "src/models/train_failure_classifier.py",
            config.ROOT / "src/models/score_cells.py",
        ),
        "SOH, RUL and failure-risk models train, score, and persist metadata.",
    ),
    ScorecardItem(
        "Battery engineering analytics",
        (
            config.ROOT / "src/ingest/generate_synthetic_battery_data.py",
            config.CELL_FEATURES_CSV,
            config.REPORTS_DIR / "high_risk_cells_summary.md",
        ),
        "Capacity fade, impedance growth, thermal exposure and EOL logic drive the analysis.",
    ),
    ScorecardItem(
        "Real public battery data validation",
        (
            config.ROOT / "src/ingest/import_public_battery_data.py",
            config.REAL_DATA_VALIDATION_REPORT,
        ),
        "Optional NASA PCoE public battery aging data adapter validates degradation trends on real cells.",
    ),
    ScorecardItem(
        "SQL warehouse and data modeling",
        (
            config.ROOT / "sql/create_schema.sql",
            config.ROOT / "sql/build_marts.sql",
            config.WAREHOUSE_DB,
        ),
        "Star schema facts/dimensions plus cell-health, factory-quality and escalation marts.",
    ),
    ScorecardItem(
        "Large-table data loading",
        (config.ROOT / "src/warehouse/build_warehouse.py", config.CYCLES_CSV),
        "Cycle facts load through a configurable chunked path for large cycler exports.",
    ),
    ScorecardItem(
        "Unix, Bash and Perl",
        (
            config.ROOT / "scripts/run_daily_pipeline.sh",
            config.ROOT / "scripts/validate_files.sh",
            config.ROOT / "scripts/parse_raw_logs.pl",
        ),
        "One-command orchestration, validation, and raw telemetry parsing.",
    ),
    ScorecardItem(
        "TCP/IP data-source operations",
        (config.ROOT / "scripts/check_data_source_connectivity.sh",),
        "Host:port preflight for lab/factory data feeds using Unix network tools.",
    ),
    ScorecardItem(
        "Tableau and JMP handoffs",
        (
            config.TABLEAU_EXTRACTS_DIR / "executive_battery_health.csv",
            config.ROOT / "dashboards/tableau_dashboard_blueprint.md",
            config.JMP_ANALYSIS_CSV,
            config.JMP_SCRIPT,
        ),
        "BI-ready CSV extracts, dashboard blueprint, and JMP CSV/JSL starter analysis.",
    ),
    ScorecardItem(
        "Statistics and value-added analysis",
        (
            config.REPORTS_DIR / "model_performance_summary.md",
            config.MODEL_MONITORING_REPORT,
            config.MODEL_MONITORING_METRICS_CSV,
        ),
        "Grouped validation, explainability, cohort PSI, risk mix, and recommended actions.",
    ),
    ScorecardItem(
        "Urgent escalation reporting",
        (
            config.REPORTS_DIR / "escalation_report_sample.csv",
            config.REPORTS_DIR / "high_risk_cells_summary.md",
        ),
        "Ranked high-risk cell queue with likely root cause and follow-up action.",
    ),
    ScorecardItem(
        "AI-powered reusable workflows",
        (
            config.ROOT / "ai_workflows/anomaly_investigation_skill.md",
            config.ROOT / "ai_workflows/sql_report_generation_skill.md",
            config.ROOT / "ai_workflows/model_debugging_workflow.md",
            config.ROOT / "ai_workflows/escalation_report_assistant.md",
        ),
        "Reusable LLM workflows for triage, SQL generation, debugging and report writing.",
    ),
    ScorecardItem(
        "Traceability and verification",
        (
            config.ROOT / "pyproject.toml",
            config.ROOT / ".github/workflows/ci.yml",
            config.ROOT / "tests/test_model_outputs.py",
            config.ROOT / "LICENSE",
        ),
        "Project metadata, CI, tests and license are present.",
    ),
]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(config.ROOT))
    except ValueError:
        return str(path)


def build_report() -> str:
    config.ensure_dirs()
    passed = 0
    lines = [
        "# Project Readiness Scorecard",
        "",
        f"_Generated: {date.today().isoformat()} - evidence-based portfolio review._",
        "",
        "| Competency | Status | Evidence | Note |",
        "| --- | --- | --- | --- |",
    ]
    for item in ITEMS:
        missing = [path for path in item.evidence if not path.exists()]
        status = "PASS" if not missing else "MISSING"
        if not missing:
            passed += 1
        evidence = "<br>".join(_rel(path) for path in item.evidence)
        if missing:
            evidence += "<br>Missing: " + ", ".join(_rel(path) for path in missing)
        lines.append(f"| {item.competency} | {status} | {evidence} | {item.note} |")

    score = f"{passed}/{len(ITEMS)}"
    verdict = "portfolio-ready" if passed == len(ITEMS) else "needs follow-up"
    lines += [
        "",
        f"## Overall Score: {score}",
        "",
        f"Verdict: **{verdict}** for a 0-2 year Battery Engineering Data Scientist contractor portfolio.",
        "",
        "This scorecard does not claim proprietary battery experience. It shows the repo has concrete, runnable evidence for the role's expected data, ML, SQL, reporting, Unix, Tableau/JMP, and AI-workflow skills.",
    ]
    md = "\n".join(lines) + "\n"
    config.PROJECT_READINESS_SCORECARD.write_text(md, encoding="utf-8")
    log.info("Wrote project readiness scorecard %s | score=%s", config.PROJECT_READINESS_SCORECARD, score)
    return md


if __name__ == "__main__":
    build_report()
