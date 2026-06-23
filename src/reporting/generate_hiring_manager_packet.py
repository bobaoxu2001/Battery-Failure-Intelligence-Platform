"""Generate the fast-review packet and single-cell investigation case study.

These reports are meant for a skeptical battery data-science reviewer: they
surface the strongest proof artifacts quickly, then walk through one concrete
cell investigation using warehouse/model outputs instead of static prose.

Run as a module::

    python -m src.reporting.generate_hiring_manager_packet
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from src import config
from src.reporting.generate_escalation_report import FOLLOW_UP, DEFAULT_FOLLOW_UP
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


PROOF_ARTIFACTS = [
    (
        "Panel interview guide",
        "docs/interview/PANEL_INTERVIEW_GUIDE.md",
        "Concise talk track for the Apple Battery DS panel, including what is real vs synthetic and how not to overclaim.",
    ),
    (
        "200-cell ad-hoc failure investigation",
        "reports/ad_hoc_200_battery_failure_investigation.md",
        "Turns the first-round prompt into a battery engineering analytics plan: label definition, SQL summaries, bias controls, validation, and actions.",
    ),
    (
        "End-to-end runnable pipeline",
        "scripts/run_daily_pipeline.sh",
        "Generates data, features, warehouse, models, scores, reports, real-data validation, and file checks.",
    ),
    (
        "Real public battery validation",
        "reports/real_data_validation_summary.md",
        "Parses NASA PCoE battery-aging data and reports capacity fade, SOH crossing, temperature, and correlation evidence.",
    ),
    (
        "Honest real-data boundary",
        "reports/real_data_coverage_and_limitations.md",
        "Separates real NASA validation from synthetic factory, usage, failure labels, and escalation thresholds.",
    ),
    (
        "NASA full-archive local-run boundary",
        "reports/nasa_full_archive_local_run_summary.md",
        "Clarifies that 34 batteries / 2,750 rows / 13 clear fade cases came from an optional local archive run, not the default committed report.",
    ),
    (
        "Battery cell investigation",
        "reports/cell_investigation_case_study.md",
        "Shows one escalated cell, peer context, likely driver, and engineering follow-up.",
    ),
    (
        "Model evidence",
        "reports/model_performance_summary.md",
        "Summarizes SOH, RUL, failure-risk metrics and explains why synthetic metrics are implementation checks.",
    ),
    (
        "Operational escalation output",
        "reports/high_risk_cells_summary.md",
        "Daily queue with risk tiers, likely root causes, and recommended engineering actions.",
    ),
    (
        "SQL warehouse and BI handoff",
        "dashboards/tableau_extracts/executive_battery_health.csv",
        "Flat extract from the modeled warehouse, ready for Tableau or another BI surface.",
    ),
    (
        "Production access discipline",
        "docs/production_data_access/production_validation_plan.md",
        "Defines authorized-only validation, holdouts, label checks, drift review, and feedback loops.",
    ),
]


def _rel(path: Path | str) -> str:
    path = Path(path)
    if not path.is_absolute():
        path = config.ROOT / path
    try:
        return str(path.relative_to(config.ROOT))
    except ValueError:
        return str(path)


def _exists(path: Path | str) -> bool:
    path = Path(path)
    if not path.is_absolute():
        path = config.ROOT / path
    return path.exists()


def _fmt_float(value: object, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def _fmt_percent(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.{digits}f}%"


def _percentile(series: pd.Series, value: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return float("nan")
    return float((numeric <= value).mean())


def _safe_text(value: object) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip()


def _load_warehouse_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        health = pd.read_sql_query("SELECT * FROM mart_cell_health_summary", conn)
        queue = pd.read_sql_query("SELECT * FROM mart_escalation_queue", conn)
        factory = pd.read_sql_query("SELECT * FROM mart_factory_quality", conn)
    return health, queue, factory


def _latest_cycle_slice(cell_id: str) -> pd.DataFrame:
    if not config.CYCLE_FEATURES_CSV.exists():
        return pd.DataFrame()
    cycles = pd.read_csv(config.CYCLE_FEATURES_CSV)
    cell_cycles = cycles[cycles["cell_id"] == cell_id].sort_values("cycle_index")
    return cell_cycles.tail(20)


def _case_study_markdown(health: pd.DataFrame, queue: pd.DataFrame, factory: pd.DataFrame) -> str:
    lines = [
        "# Battery Cell Investigation Case Study",
        "",
        f"_Generated: {date.today().isoformat()} - synthetic factory/usage/failure data; no confidential data used._",
        "",
    ]
    if queue.empty:
        lines += [
            "No cells are currently in the escalation queue.",
            "",
            "The pipeline still produced the warehouse, predictions, monitoring outputs, and real-data validation reports.",
        ]
        return "\n".join(lines) + "\n"

    target = queue.sort_values(
        ["failure_probability", "predicted_remaining_cycles"],
        ascending=[False, True],
    ).iloc[0]
    cell_id = str(target["cell_id"])
    cell = health[health["cell_id"] == cell_id].iloc[0]
    driver = _safe_text(target.get("top_risk_driver", "Unknown"))
    follow_up = FOLLOW_UP.get(str(target.get("top_risk_driver")), DEFAULT_FOLLOW_UP)
    cycle_tail = _latest_cycle_slice(cell_id)

    fade_pct = _percentile(health["capacity_fade_rate"], float(cell["capacity_fade_rate"]))
    resistance_pct = _percentile(health["resistance_growth_rate"], float(cell["resistance_growth_rate"]))
    temp_pct = _percentile(health["peak_temperature_max"], float(cell["peak_temperature_max"]))
    soh_pct = _percentile(health["last_soh"], float(cell["last_soh"]))

    lot = str(cell["lot_id"])
    station = str(cell["station_id"])
    lot_station = factory[(factory["lot_id"] == lot) & (factory["station_id"] == station)]
    lot_mean_escalation = factory[factory["lot_id"] == lot]["escalation_rate"].mean()
    station_mean_escalation = factory[factory["station_id"] == station]["escalation_rate"].mean()

    lines += [
        "## Selected Cell",
        "",
        f"Selected the highest-risk current queue item: **{cell_id}**.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Lot / station | {lot} / {station} |",
        f"| Usage profile | {_safe_text(cell['usage_profile'])} |",
        f"| Risk tier | {_safe_text(cell['risk_tier'])} |",
        f"| Failure probability | {_fmt_float(cell['failure_probability'], 4)} |",
        f"| Predicted SOH | {_fmt_float(cell['predicted_soh'], 4)} |",
        f"| Last observed SOH | {_fmt_float(cell['last_soh'], 4)} |",
        f"| Predicted remaining cycles | {_fmt_float(cell['predicted_remaining_cycles'], 1)} |",
        f"| Model top driver | {driver} |",
        f"| Engineering follow-up | {_safe_text(follow_up)} |",
        "",
        "## Peer Context",
        "",
        "| Signal | Cell value | Fleet percentile | Why it matters |",
        "| --- | --- | --- | --- |",
        f"| Capacity fade rate | {_fmt_float(cell['capacity_fade_rate'], 6)} | {_fmt_percent(fade_pct)} | Higher fade rate indicates accelerated loss of usable capacity. |",
        f"| Resistance growth rate | {_fmt_float(cell['resistance_growth_rate'], 6)} | {_fmt_percent(resistance_pct)} | Rising resistance can point to aging, contact, tab-weld, or impedance-growth issues. |",
        f"| Peak temperature max | {_fmt_float(cell['peak_temperature_max'], 1)} C | {_fmt_percent(temp_pct)} | Thermal exposure can accelerate degradation and needs sensor/protocol review. |",
        f"| Last observed SOH | {_fmt_float(cell['last_soh'], 4)} | {_fmt_percent(soh_pct)} | Low percentile means the cell sits among the weakest cells in the fleet. |",
        "",
        "## Lot And Station Context",
        "",
        "| Context | Escalation signal |",
        "| --- | --- |",
        f"| Same lot average escalation rate | {_fmt_percent(lot_mean_escalation)} |",
        f"| Same station average escalation rate | {_fmt_percent(station_mean_escalation)} |",
    ]
    if not lot_station.empty:
        row = lot_station.iloc[0]
        lines.append(f"| Same lot-station escalation rate | {_fmt_percent(row['escalation_rate'])} |")
        lines.append(f"| Same lot-station early degradation rate | {_fmt_percent(row['early_degradation_rate'])} |")

    if not cycle_tail.empty:
        first = cycle_tail.iloc[0]
        last = cycle_tail.iloc[-1]
        soh_delta = float(last["soh_current"]) - float(first["soh_current"])
        lines += [
            "",
            "## Recent Cycle Window",
            "",
            "| Window | SOH start | SOH end | Delta | Max rolling temp C |",
            "| --- | --- | --- | --- | --- |",
            (
                f"| Last {len(cycle_tail)} cycles | {_fmt_float(first['soh_current'], 4)} | "
                f"{_fmt_float(last['soh_current'], 4)} | {_fmt_float(soh_delta, 4)} | "
                f"{_fmt_float(cycle_tail['rolling_temperature_max_10'].max(), 1)} |"
            ),
        ]

    lines += [
        "",
        "## Decision",
        "",
        "1. Confirm the SOH estimate with a reference performance test.",
        f"2. Execute the recommended follow-up: {_safe_text(follow_up)}",
        "3. Compare this cell with same-lot and same-station peers before deciding whether the issue is isolated or systemic.",
        "",
        "## Boundary",
        "",
        "This is a synthetic production-style investigation. It demonstrates the analysis loop, warehouse joins, peer comparison, and escalation writing. It does not claim a validated production false-positive rate without authorized real factory, usage, failure-label, and disposition data.",
    ]
    return "\n".join(lines) + "\n"


def _packet_markdown() -> str:
    passed = sum(1 for _, path, _ in PROOF_ARTIFACTS if _exists(path))
    lines = [
        "# Hiring Manager Review Packet",
        "",
        f"_Generated: {date.today().isoformat()} - fast review guide for a battery data-science hiring manager._",
        "",
        "## First 60 Seconds",
        "",
        "This project is strongest when reviewed as an engineering analytics system: battery data ingestion, SQL warehouse, leakage-aware ML, escalation reporting, BI/JMP handoffs, and real public NASA validation with clear limits.",
        "",
        "Recommended skim path:",
        "",
        "1. Read `docs/interview/PANEL_INTERVIEW_GUIDE.md` for the panel talk track.",
        "2. Read `reports/ad_hoc_200_battery_failure_investigation.md` for the 200-cell pass/fail prompt.",
        "3. Read `reports/cell_investigation_case_study.md` for one concrete escalation investigation.",
        "4. Read `reports/real_data_validation_summary.md` for real NASA battery-aging evidence.",
        "5. Read `reports/nasa_full_archive_local_run_summary.md` for the default-vs-full-archive NASA boundary.",
        "6. Read `reports/real_data_coverage_and_limitations.md` for the honest production boundary.",
        "7. Read `reports/project_readiness_scorecard.md` to map role expectations to files.",
        "",
        f"## Evidence Map ({passed}/{len(PROOF_ARTIFACTS)} Present)",
        "",
        "| Proof point | Artifact | Why it matters | Status |",
        "| --- | --- | --- | --- |",
    ]
    for proof, path, why in PROOF_ARTIFACTS:
        status = "present" if _exists(path) else "missing"
        lines.append(f"| {_safe_text(proof)} | `{_rel(path)}` | {_safe_text(why)} | {status} |")

    lines += [
        "",
        "## What To Ask Me In An Interview",
        "",
        "- How I prevented target leakage in cell-level validation and group-rate features.",
        "- Why the synthetic model metrics are treated as implementation checks instead of production accuracy claims.",
        "- How the NASA adapter handles clear fade cases versus protocol windows with increasing capacity or weak correlation.",
        "- How I would validate the same pipeline with authorized factory, usage, quality-hold, retest, and disposition data.",
        "- Which escalation thresholds I would tune with battery engineers before production use.",
        "",
        "## What I Would Improve With Team Access",
        "",
        "- Replace synthetic factory and usage records with governed read-only production tables.",
        "- Backtest false positives and missed escalations by lot, station, protocol, supplier, and time window.",
        "- Add engineer disposition labels to close the feedback loop from alert to action.",
        "- Serve the daily queue through the team's preferred BI/escalation surface instead of local CSV/Markdown artifacts.",
        "",
        "## Boundary",
        "",
        "No confidential or proprietary data is used. The default factory/usage/failure pipeline is synthetic, the NASA degradation layer is public, and the production connector is an authorized-only scaffold.",
    ]
    return "\n".join(lines) + "\n"


def generate() -> tuple[str, str]:
    config.ensure_dirs()
    health, queue, factory = _load_warehouse_tables()

    case_study = _case_study_markdown(health, queue, factory)
    config.CELL_INVESTIGATION_CASE_STUDY.write_text(case_study, encoding="utf-8")
    log.info("Wrote %s", config.CELL_INVESTIGATION_CASE_STUDY)

    packet = _packet_markdown()
    config.HIRING_MANAGER_PACKET.write_text(packet, encoding="utf-8")
    log.info("Wrote %s", config.HIRING_MANAGER_PACKET)
    return packet, case_study


if __name__ == "__main__":
    generate()
