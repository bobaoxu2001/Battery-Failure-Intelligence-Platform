"""Generate the urgent engineering escalation outputs.

Reads the warehouse escalation queue (model High/Critical risk OR an existing
escalation flag) and produces two recruiter-/engineer-facing artifacts:

* ``reports/escalation_report_sample.csv`` - machine-readable queue with a
  likely root cause and a recommended engineering follow-up per cell.
* ``reports/high_risk_cells_summary.md``  - a readable daily standup summary.

Run as a module::

    python -m src.reporting.generate_escalation_report
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

# Map the model's top_risk_driver to a concrete engineering follow-up action.
FOLLOW_UP = {
    "Accelerated capacity fade": "Pull cell for teardown; check anode lithium plating and electrolyte loss.",
    "Internal resistance growth": "Run EIS impedance sweep; inspect tab welds and contact resistance.",
    "Peak thermal exposure": "Audit thermal management / cooling path; verify ambient test conditions.",
    "Sustained thermal exposure": "Review duty cycle thermal load; validate temperature sensor calibration.",
    "High-temperature field exposure": "Flag usage profile to reliability; recommend thermal derating.",
    "Heavy fast-charge usage": "Review fast-charge current limits; check for lithium plating signatures.",
    "Deep discharge cycling": "Recommend depth-of-discharge limit; review BMS cutoff thresholds.",
    "Low state of health": "Prioritise for replacement; confirm capacity with reference performance test.",
    "Test-station anomaly signal": "Re-test on a reference station; audit station calibration drift.",
    "Low-temperature exposure": "Review low-temp charging policy; check for plating under cold charge.",
    "High cumulative cycle count": "Expected wear-out; confirm against cycle-life spec and schedule rotation.",
}
DEFAULT_FOLLOW_UP = "Manual engineering review of cycling history and factory record."


def _likely_root_cause(row: pd.Series) -> str:
    """Refine the model driver with hard signals from the failure record."""
    driver = row.get("top_risk_driver") or "Unknown"
    if row.get("failure_severity") == "critical" and row.get("last_soh", 1) < config.SOH_EOL_THRESHOLD:
        return f"{driver} (cell already below {config.SOH_EOL_THRESHOLD:.0%} SOH)"
    return driver


def generate() -> pd.DataFrame:
    config.ensure_dirs()
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        queue = pd.read_sql_query("SELECT * FROM mart_escalation_queue", conn)

    if queue.empty:
        log.warning("Escalation queue is empty - writing headers only")

    queue["likely_root_cause"] = queue.apply(_likely_root_cause, axis=1)
    queue["recommended_follow_up"] = queue["top_risk_driver"].map(FOLLOW_UP).fillna(DEFAULT_FOLLOW_UP)

    # Machine-readable escalation CSV with the contracted columns.
    out_cols = [
        "cell_id", "lot_id", "station_id", "failure_probability", "predicted_soh",
        "predicted_remaining_cycles", "likely_root_cause", "recommended_follow_up",
    ]
    escalation_csv = queue[out_cols].sort_values("failure_probability", ascending=False)
    csv_path = config.REPORTS_DIR / "escalation_report_sample.csv"
    escalation_csv.to_csv(csv_path, index=False)
    log.info("Wrote %s (%d cells)", csv_path, len(escalation_csv))

    _write_markdown(queue)
    return escalation_csv


def _write_markdown(queue: pd.DataFrame) -> None:
    n = len(queue)
    crit = int((queue["risk_tier"] == "Critical").sum())
    high = int((queue["risk_tier"] == "High").sum())
    top = queue.sort_values("failure_probability", ascending=False).head(15)

    lines = [
        "# High-Risk Battery Cells - Daily Escalation Summary",
        "",
        f"_Generated: {date.today().isoformat()} • synthetic data; no Apple confidential data used._",
        "",
        f"**{n} cells** require engineering attention today "
        f"(**{crit} Critical**, **{high} High**).",
        "",
        "## Top cells in the escalation queue",
        "",
        "| Cell | Lot | Station | Risk | Fail prob | Pred SOH | Rem. cycles | Likely root cause | Recommended follow-up |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, r in top.iterrows():
        cause = r["top_risk_driver"]
        follow = FOLLOW_UP.get(cause, DEFAULT_FOLLOW_UP)
        lines.append(
            f"| {r['cell_id']} | {r['lot_id']} | {r['station_id']} | {r['risk_tier']} | "
            f"{r['failure_probability']:.3f} | {r['predicted_soh']:.3f} | "
            f"{r['predicted_remaining_cycles']:.0f} | {cause} | {follow} |"
        )

    # Lot-level rollup so engineering can spot a systemic factory issue.
    lot_roll = (queue.groupby("lot_id").size().sort_values(ascending=False).head(5))
    lines += ["", "## Lots with the most escalations", "", "| Lot | Escalated cells |", "| --- | --- |"]
    for lot, cnt in lot_roll.items():
        lines.append(f"| {lot} | {cnt} |")

    lines += [
        "",
        "## Recommended actions",
        "1. Triage all **Critical** cells first; confirm SOH with a reference performance test.",
        "2. For lots above the fleet escalation rate, hold the lot and open a factory-quality investigation.",
        "3. Re-test any cell whose driver is a *test-station anomaly* on a reference station before scrapping.",
        "",
        "_See `reports/escalation_report_sample.csv` for the full machine-readable queue._",
    ]
    out = config.REPORTS_DIR / "high_risk_cells_summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote %s", out)


if __name__ == "__main__":
    generate()
