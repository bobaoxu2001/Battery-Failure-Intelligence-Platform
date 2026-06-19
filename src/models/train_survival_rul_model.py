"""Train a censored, survival-style RUL model.

The standard RUL regressor uses per-cycle targets. This module adds a
cell-level time-to-EOL model that handles right-censoring: cells that do not
cross 80% SOH still contribute safe observed intervals, then stop contributing
after their last observed cycle.

Implementation: discrete-time hazard model with 50-cycle intervals and a
logistic classifier. This avoids a heavyweight survival dependency while
preserving the important modeling contract: censored rows are not mislabeled as
never-failures.

Run as a module::

    python -m src.models.train_survival_rul_model
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

SURVIVAL_MODEL_PATH = config.MODELS_DIR / "survival_rul_model.joblib"
INTERVAL_WIDTH = 50
NUMERIC_FEATURES = [
    "fast_charge_ratio",
    "avg_depth_of_discharge",
    "high_temp_exposure_hours",
    "low_temp_exposure_hours",
    "station_anomaly_rate",
]
CATEGORICAL_FEATURES = ["usage_profile"]


@dataclass
class SurvivalBundle:
    estimator: Pipeline
    interval_width: int
    features: list[str]
    train_event_rate: float
    train_median_event_cycle: float
    metrics: dict

    def save(self, path= SURVIVAL_MODEL_PATH) -> None:
        # When this file is executed with `python -m`, pickle would otherwise
        # record the dataclass as `__main__.SurvivalBundle`, which cannot be
        # loaded later from tests or downstream modules.
        sys.modules.setdefault("src.models.train_survival_rul_model", sys.modules[__name__])
        self.__class__.__module__ = "src.models.train_survival_rul_model"
        joblib.dump(self, path)

    @staticmethod
    def load(path= SURVIVAL_MODEL_PATH) -> "SurvivalBundle":
        return joblib.load(path)


def _cell_survival_frame() -> pd.DataFrame:
    cycle = pd.read_csv(config.CYCLE_FEATURES_CSV)
    cell = pd.read_csv(config.CELL_FEATURES_CSV)
    rows = []
    for cell_id, group in cycle.groupby("cell_id"):
        group = group.sort_values("cycle_index")
        event_rows = group[group["soh_current"] < config.SOH_EOL_THRESHOLD]
        event_observed = int(not event_rows.empty)
        event_cycle = int(event_rows["cycle_index"].iloc[0]) if event_observed else int(group["cycle_index"].max())
        rows.append({"cell_id": cell_id, "duration_cycles": event_cycle, "event_observed": event_observed})
    durations = pd.DataFrame(rows)
    return cell.merge(durations, on="cell_id", how="inner")


def _release_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    factory = pd.read_csv(config.FACTORY_CSV, parse_dates=["manufacturing_date"])[["cell_id", "manufacturing_date"]]
    merged = frame.merge(factory, on="cell_id", how="left").sort_values(["manufacturing_date", "cell_id"])
    cut = max(1, min(len(merged) - 1, int(len(merged) * 0.70)))
    cutoff = merged.iloc[cut - 1]["manufacturing_date"].date().isoformat()
    return merged.iloc[:cut].copy(), merged.iloc[cut:].copy(), cutoff


def _expand_intervals(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in frame.itertuples(index=False):
        duration = int(getattr(row, "duration_cycles"))
        event_observed = int(getattr(row, "event_observed"))
        max_interval = max(INTERVAL_WIDTH, int(np.ceil(duration / INTERVAL_WIDTH) * INTERVAL_WIDTH))
        for interval_end in range(INTERVAL_WIDTH, max_interval + 1, INTERVAL_WIDTH):
            if interval_end > duration and not event_observed:
                break
            hazard = int(event_observed and duration <= interval_end)
            item = {name: getattr(row, name) for name in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
            item.update(
                {
                    "cell_id": getattr(row, "cell_id"),
                    "interval_end": interval_end,
                    "log_interval_end": float(np.log1p(interval_end)),
                    "hazard_event": hazard,
                }
            )
            rows.append(item)
            if hazard:
                break
    return pd.DataFrame(rows)


def _build_estimator() -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES + ["log_interval_end"]),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=config.SEED)
    return Pipeline([("preprocess", pre), ("hazard", clf)])


def _predict_distribution(bundle: SurvivalBundle, cells: pd.DataFrame, max_horizon: int) -> pd.DataFrame:
    rows = []
    horizon = int(np.ceil(max_horizon / bundle.interval_width) * bundle.interval_width)
    for row in cells.itertuples(index=False):
        survival = 1.0
        expected_event = 0.0
        median_cycle = horizon
        crossed_median = False
        cumulative_event = 0.0
        risk_by_500 = 0.0
        for interval_end in range(bundle.interval_width, horizon + 1, bundle.interval_width):
            item = {name: getattr(row, name) for name in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
            item["interval_end"] = interval_end
            item["log_interval_end"] = float(np.log1p(interval_end))
            x = pd.DataFrame([item])
            hazard = float(bundle.estimator.predict_proba(x)[0, 1])
            interval_event_prob = survival * hazard
            expected_event += interval_end * interval_event_prob
            survival *= (1.0 - hazard)
            cumulative_event = 1.0 - survival
            if interval_end <= 500:
                risk_by_500 = cumulative_event
            if not crossed_median and survival <= 0.5:
                median_cycle = interval_end
                crossed_median = True
        if survival > 0:
            expected_event += horizon * survival
        observed_duration = int(getattr(row, "duration_cycles"))
        rows.append(
            {
                "cell_id": getattr(row, "cell_id"),
                "event_observed": int(getattr(row, "event_observed")),
                "observed_duration_cycles": observed_duration,
                "predicted_median_eol_cycle": int(median_cycle),
                "predicted_expected_eol_cycle": float(expected_event),
                "predicted_remaining_cycles_from_observed": max(float(expected_event - observed_duration), 0.0),
                "event_probability_by_horizon": float(cumulative_event),
                "event_probability_by_500_cycles": float(risk_by_500),
            }
        )
    return pd.DataFrame(rows)


def _concordance_index(frame: pd.DataFrame) -> float:
    comparable = permissible = concordant = ties = 0
    rows = frame.to_dict("records")
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["observed_duration_cycles"] == b["observed_duration_cycles"]:
                continue
            if not a["event_observed"] and not b["event_observed"]:
                continue
            earlier, later = (a, b) if a["observed_duration_cycles"] < b["observed_duration_cycles"] else (b, a)
            if not earlier["event_observed"]:
                continue
            permissible += 1
            if earlier["event_probability_by_500_cycles"] > later["event_probability_by_500_cycles"]:
                concordant += 1
            elif earlier["event_probability_by_500_cycles"] == later["event_probability_by_500_cycles"]:
                ties += 1
    comparable = permissible
    if comparable == 0:
        return float("nan")
    return float((concordant + 0.5 * ties) / comparable)


def train() -> SurvivalBundle:
    config.ensure_dirs()
    frame = _cell_survival_frame()
    train_cells, test_cells, cutoff = _release_split(frame)
    expanded = _expand_intervals(train_cells)
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["log_interval_end"]
    estimator = _build_estimator()
    estimator.fit(expanded[features], expanded["hazard_event"].astype(int))

    event_cycles = train_cells.loc[train_cells["event_observed"] == 1, "duration_cycles"]
    median_event = float(event_cycles.median()) if not event_cycles.empty else float(train_cells["duration_cycles"].median())
    bundle = SurvivalBundle(
        estimator=estimator,
        interval_width=INTERVAL_WIDTH,
        features=features,
        train_event_rate=float(train_cells["event_observed"].mean()),
        train_median_event_cycle=median_event,
        metrics={},
    )
    predictions = _predict_distribution(bundle, test_cells, max_horizon=int(frame["duration_cycles"].max()))
    event_eval = predictions[predictions["event_observed"] == 1]
    baseline_pred = np.repeat(median_event, len(event_eval))
    if not event_eval.empty:
        model_mae = float(mean_absolute_error(event_eval["observed_duration_cycles"], event_eval["predicted_expected_eol_cycle"]))
        baseline_mae = float(mean_absolute_error(event_eval["observed_duration_cycles"], baseline_pred))
    else:
        model_mae = baseline_mae = float("nan")
    metrics = {
        "train_cells": int(len(train_cells)),
        "test_cells": int(len(test_cells)),
        "train_event_rate": float(train_cells["event_observed"].mean()),
        "test_event_rate": float(test_cells["event_observed"].mean()),
        "event_cycle_mae": model_mae,
        "median_baseline_event_cycle_mae": baseline_mae,
        "concordance_index": _concordance_index(predictions),
        "manufacturing_cutoff": cutoff,
    }
    bundle.metrics = metrics
    bundle.save()
    predictions.to_csv(config.SURVIVAL_PREDICTIONS_CSV, index=False)
    build_report(bundle, predictions)
    log.info("Saved censored RUL survival model -> %s", SURVIVAL_MODEL_PATH)
    return bundle


def build_report(bundle: SurvivalBundle, predictions: pd.DataFrame | None = None) -> str:
    if predictions is None:
        predictions = pd.read_csv(config.SURVIVAL_PREDICTIONS_CSV)
    m = bundle.metrics
    lines = [
        "# Censored RUL Survival Model",
        "",
        f"_Generated: {date.today().isoformat()}._",
        "",
        "This model estimates time-to-80% SOH with right-censoring. Cells that never cross the EOL threshold are treated as observed-safe until their final recorded cycle, not as permanent non-failures.",
        "",
        "## Model Design",
        "",
        f"- Interval width: {bundle.interval_width} cycles",
        "- Estimator: logistic discrete-time hazard model",
        f"- Features: {', '.join(f'`{x}`' for x in bundle.features)}",
        f"- Training cells: {m['train_cells']}",
        f"- Holdout cells: {m['test_cells']}",
        f"- Manufacturing-date cutoff: {m['manufacturing_cutoff']}",
        "",
        "## Holdout Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Train event rate | {m['train_event_rate']:.3f} |",
        f"| Holdout event rate | {m['test_event_rate']:.3f} |",
        f"| Event-cycle MAE | {m['event_cycle_mae']:.1f} cycles |",
        f"| Median-event baseline MAE | {m['median_baseline_event_cycle_mae']:.1f} cycles |",
        f"| Concordance index | {m['concordance_index']:.3f} |",
        "",
        "## Sample Holdout Predictions",
        "",
        "| Cell | Event observed | Observed duration | Pred expected EOL | Pred remaining from observed | Event probability by 500 cycles |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in predictions.sort_values("event_probability_by_500_cycles", ascending=False).head(10).iterrows():
        lines.append(
            f"| {row['cell_id']} | {int(row['event_observed'])} | {int(row['observed_duration_cycles'])} | "
            f"{row['predicted_expected_eol_cycle']:.1f} | {row['predicted_remaining_cycles_from_observed']:.1f} | "
            f"{row['event_probability_by_500_cycles']:.3f} |"
        )
    lines += [
        "",
        "## Why this matters",
        "",
        "A standard RUL regressor needs a numeric remaining-life target for every row. Real battery programs often have cells that have not failed yet, so the target is censored. This module shows the release path for that more realistic setting without pretending censored cells have known final lifetimes.",
    ]
    md = "\n".join(lines) + "\n"
    config.SURVIVAL_RUL_REPORT.write_text(md, encoding="utf-8")
    return md


if __name__ == "__main__":
    train()
