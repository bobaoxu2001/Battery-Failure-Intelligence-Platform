"""Monitor data/model behavior across manufacturing cohorts.

The project is synthetic, so there is no external production baseline. Instead,
this report compares earlier manufactured cells against the most recent 30% of
cells by manufacturing date. That mirrors a practical battery reliability review:
"did the latest lots/stations shift in health, risk, or degradation drivers?"

Run as a module::

    python -m src.models.monitor_drift
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

MONITORED_FEATURES = [
    "final_soh",
    "capacity_fade_rate",
    "resistance_growth_rate",
    "peak_temperature_max",
    "fast_charge_ratio",
    "high_temp_exposure_hours",
    "failure_probability",
]


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """Compute PSI between a reference and current numeric distribution."""
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    cur = pd.to_numeric(current, errors="coerce").dropna()
    if ref.empty or cur.empty:
        return float("nan")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_pct = np.histogram(ref, bins=edges)[0] / len(ref)
    cur_pct = np.histogram(cur, bins=edges)[0] / len(cur)
    ref_pct = np.clip(ref_pct, 1e-6, None)
    cur_pct = np.clip(cur_pct, 1e-6, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def psi_status(psi: float) -> str:
    if np.isnan(psi):
        return "unknown"
    if psi >= 0.25:
        return "alert"
    if psi >= 0.10:
        return "watch"
    return "ok"


def _read_monitoring_frame() -> pd.DataFrame:
    factory = pd.read_csv(config.FACTORY_CSV, parse_dates=["manufacturing_date"])
    features = pd.read_csv(config.CELL_FEATURES_CSV)
    predictions = pd.read_csv(config.PREDICTIONS_CSV)
    df = (
        features
        .merge(factory[["cell_id", "manufacturing_date", "equipment_id"]], on="cell_id", how="left")
        .merge(predictions[["cell_id", "failure_probability", "risk_tier", "top_risk_driver"]], on="cell_id", how="left")
        .sort_values(["manufacturing_date", "cell_id"])
        .reset_index(drop=True)
    )
    if df.empty:
        raise ValueError("Monitoring frame is empty; run the daily pipeline first")
    return df


def _split_cohorts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = max(1, int(len(df) * 0.70))
    if cutoff >= len(df):
        cutoff = max(1, len(df) - 1)
    reference = df.iloc[:cutoff].copy()
    current = df.iloc[cutoff:].copy()
    if current.empty:
        current = reference.copy()
    return reference, current


def build_monitoring_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = _read_monitoring_frame()
    reference, current = _split_cohorts(df)

    rows = []
    for feature in MONITORED_FEATURES:
        ref_mean = float(reference[feature].mean())
        cur_mean = float(current[feature].mean())
        rows.append(
            {
                "feature": feature,
                "reference_mean": ref_mean,
                "current_mean": cur_mean,
                "delta": cur_mean - ref_mean,
                "psi": population_stability_index(reference[feature], current[feature]),
            }
        )
    metrics = pd.DataFrame(rows)
    metrics["status"] = metrics["psi"].map(psi_status)

    risk = (
        current["risk_tier"]
        .value_counts()
        .rename_axis("risk_tier")
        .reset_index(name="current_cells")
        .sort_values("risk_tier")
    )
    drivers = (
        current["top_risk_driver"]
        .value_counts()
        .head(8)
        .rename_axis("top_risk_driver")
        .reset_index(name="current_cells")
    )
    return metrics, risk, drivers


def _markdown_table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["_No rows._"]
    lines = ["| " + " | ".join(df.columns) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.iterrows():
        rendered = []
        for value in row:
            if isinstance(value, float):
                rendered.append(f"{value:.4f}")
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    return lines


def build_report() -> str:
    config.ensure_dirs()
    metrics, risk, drivers = build_monitoring_tables()
    metrics.to_csv(config.MODEL_MONITORING_METRICS_CSV, index=False)

    worst = metrics.sort_values("psi", ascending=False).head(5)
    alerts = metrics[metrics["status"].isin(["watch", "alert"])]
    status_text = "No material cohort drift detected." if alerts.empty else (
        f"{len(alerts)} monitored feature(s) are in watch/alert status."
    )

    md_lines = [
        "# Model Monitoring Summary",
        "",
        f"_Generated: {date.today().isoformat()} - synthetic cohort monitoring._",
        "",
        status_text,
        "",
        "## Feature Stability",
        "",
        *(_markdown_table(worst[["feature", "reference_mean", "current_mean", "delta", "psi", "status"]])),
        "",
        "## Current Cohort Risk Mix",
        "",
        *(_markdown_table(risk)),
        "",
        "## Current Cohort Leading Drivers",
        "",
        *(_markdown_table(drivers)),
        "",
        "## Operating Guidance",
        "1. Treat `alert` PSI features as candidates for root-cause review by lot/station.",
        "2. If risk mix shifts toward High/Critical, inspect the escalation queue before retraining.",
        "3. Re-run after each daily pipeline refresh and compare the generated CSV over time.",
    ]
    md = "\n".join(md_lines) + "\n"
    config.MODEL_MONITORING_REPORT.write_text(md, encoding="utf-8")
    log.info("Wrote model monitoring metrics %s", config.MODEL_MONITORING_METRICS_CSV)
    log.info("Wrote model monitoring report %s", config.MODEL_MONITORING_REPORT)
    return md


if __name__ == "__main__":
    build_report()
