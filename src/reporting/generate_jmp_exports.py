"""Generate JMP-ready analysis files for battery reliability review.

JMP is often used by engineering teams for quick DOE-style exploration,
distribution checks and fit-model workflows. This module exports a clean cell-
level CSV plus a small JSL starter script so the same pipeline artifacts can be
opened directly in JMP without manual column wrangling.

Run as a module::

    python -m src.reporting.generate_jmp_exports
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


JMP_COLUMNS = [
    "cell_id",
    "lot_id",
    "batch_id",
    "station_id",
    "usage_profile",
    "cycle_count",
    "last_soh",
    "predicted_soh",
    "predicted_remaining_cycles",
    "failure_probability",
    "risk_tier",
    "top_risk_driver",
    "capacity_fade_rate",
    "resistance_growth_rate",
    "peak_temperature_max",
    "escalation_required",
    "failure_severity",
]


def _read_cell_health() -> pd.DataFrame:
    sql = f"""
        SELECT {", ".join(JMP_COLUMNS)}
        FROM mart_cell_health_summary
        ORDER BY failure_probability DESC, predicted_remaining_cycles ASC
    """
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        return pd.read_sql_query(sql, conn)


def _write_jsl(csv_path) -> str:
    csv_for_jsl = csv_path.name
    script = f"""// Battery Failure Intelligence - JMP starter analysis
// Generated {date.today().isoformat()}; all data synthetic.
// Save this script next to {csv_for_jsl}, open it in JMP, then run it.

Names Default To Here(1);

dt = Open("{csv_for_jsl}");

dt << Distribution(
    Continuous Distribution(Column(:predicted_soh)),
    Continuous Distribution(Column(:predicted_remaining_cycles)),
    Continuous Distribution(Column(:failure_probability)),
    Nominal Distribution(Column(:risk_tier)),
    Nominal Distribution(Column(:top_risk_driver))
);

dt << Graph Builder(
    Size(1000, 620),
    Show Control Panel(0),
    Variables(
        X(:predicted_remaining_cycles),
        Y(:predicted_soh),
        Color(:failure_probability),
        Wrap(:risk_tier)
    ),
    Elements(Points(X, Y, Legend(9)))
);

dt << Fit Model(
    Y(:failure_probability),
    Effects(
        :last_soh,
        :capacity_fade_rate,
        :resistance_growth_rate,
        :peak_temperature_max,
        :cycle_count
    ),
    Personality("Standard Least Squares"),
    Run
);
"""
    config.JMP_SCRIPT.write_text(script, encoding="utf-8")
    return script


def generate() -> pd.DataFrame:
    """Write ``reports/jmp_cell_analysis.csv`` and a companion JSL script."""
    config.ensure_dirs()
    df = _read_cell_health()
    if df.empty:
        log.warning("JMP export source mart is empty - writing headers only")
    df.to_csv(config.JMP_ANALYSIS_CSV, index=False)
    _write_jsl(config.JMP_ANALYSIS_CSV)
    log.info("Wrote JMP export %s (%d cells)", config.JMP_ANALYSIS_CSV, len(df))
    log.info("Wrote JMP starter script %s", config.JMP_SCRIPT)
    return df


if __name__ == "__main__":
    generate()
