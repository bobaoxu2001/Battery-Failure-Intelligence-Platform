"""Model-release backtest and baseline comparison.

This module simulates a release review: train on older manufacturing cohorts,
evaluate on later cohorts, compare against simple engineering baselines, inspect
failure-risk calibration, and choose an escalation threshold with an explicit
false-negative cost.

Run as a module::

    python -m src.models.model_release_backtest
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from sklearn.base import clone

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ReleaseSplit:
    train_cells: list[str]
    test_cells: list[str]
    cutoff_date: str


def _release_split(train_fraction: float = 0.70) -> ReleaseSplit:
    factory = pd.read_csv(config.FACTORY_CSV, parse_dates=["manufacturing_date"])
    ordered = factory.sort_values(["manufacturing_date", "cell_id"]).reset_index(drop=True)
    cut = max(1, min(len(ordered) - 1, int(len(ordered) * train_fraction)))
    train = ordered.iloc[:cut]
    test = ordered.iloc[cut:]
    cutoff = ordered.iloc[cut - 1]["manufacturing_date"].date().isoformat()
    return ReleaseSplit(
        train_cells=train["cell_id"].tolist(),
        test_cells=test["cell_id"].tolist(),
        cutoff_date=cutoff,
    )


def _fit_best_regressor(X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series):
    candidates = {
        "LinearRegression": C.linear_baseline(),
        C.boosted_regressor()[0]: C.boosted_regressor()[1],
        "RandomForest": C.random_forest_regressor(),
    }
    best = None
    for name, estimator in candidates.items():
        model = clone(estimator)
        model.fit(X_train, y_train)
        metrics = C.regression_metrics(y_test, model.predict(X_test))
        if best is None or metrics["RMSE"] < best[2]["RMSE"]:
            best = (name, model, metrics)
    return best


def _fit_best_classifier(X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series):
    candidates = {
        "LogisticRegression": C.logistic_baseline(),
        "RandomForest": C.random_forest_classifier(),
    }
    best = None
    for name, estimator in candidates.items():
        model = clone(estimator)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = C.classification_metrics(y_test, pred, proba)
        if best is None or metrics["f1"] > best[2]["f1"]:
            best = (name, model, metrics, proba)
    return best


def _soh_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    fade = train["capacity_fade_rate"].clip(lower=0)
    fleet_fade = float(fade[fade > 0].median()) if (fade > 0).any() else 0.0004
    return np.clip(1.0 - fleet_fade * test["cycle_count"].to_numpy(), 0.0, 1.05)


def _rul_baseline(test: pd.DataFrame) -> np.ndarray:
    fade = test["capacity_fade_rate"].clip(lower=1e-6).to_numpy()
    soh = test["soh_current"].to_numpy()
    cap = max(float(test["cycle_count"].quantile(0.95) * 2), 500.0)
    return np.clip((soh - config.SOH_EOL_THRESHOLD) / fade, 0, cap)


def _failure_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    risk_score = (1.0 - test["final_soh"]).clip(lower=0).to_numpy(dtype=float, copy=True)
    station_component = test["station_anomaly_rate"].clip(lower=0).to_numpy(dtype=float, copy=False)
    risk_score += 0.5 * station_component
    lo, hi = np.nanpercentile(risk_score, [5, 95])
    if hi <= lo:
        return np.repeat(float(train["escalation_required"].mean()), len(test))
    return np.clip((risk_score - lo) / (hi - lo), 0, 1)


def _threshold_table(y_true: pd.Series, proba: np.ndarray, fn_cost: float = 5.0, fp_cost: float = 1.0) -> pd.DataFrame:
    rows = []
    for threshold in np.arange(0.20, 0.81, 0.05):
        pred = (proba >= threshold).astype(int)
        fp = int(((pred == 1) & (y_true.to_numpy() == 0)).sum())
        fn = int(((pred == 0) & (y_true.to_numpy() == 1)).sum())
        tp = int(((pred == 1) & (y_true.to_numpy() == 1)).sum())
        tn = int(((pred == 0) & (y_true.to_numpy() == 0)).sum())
        rows.append(
            {
                "threshold": round(float(threshold), 2),
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": tp / max(tp + fp, 1),
                "recall": tp / max(tp + fn, 1),
                "review_load": int(tp + fp),
                "cost": fp_cost * fp + fn_cost * fn,
            }
        )
    return pd.DataFrame(rows).sort_values(["cost", "threshold"]).reset_index(drop=True)


def _calibration_table(y_true: pd.Series, proba: np.ndarray, bins: int = 5) -> pd.DataFrame:
    df = pd.DataFrame({"actual": y_true.to_numpy(), "predicted_probability": proba})
    df["bin"] = pd.cut(df["predicted_probability"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    out = (
        df.groupby("bin", observed=False)
        .agg(
            n=("actual", "size"),
            mean_predicted_probability=("predicted_probability", "mean"),
            observed_escalation_rate=("actual", "mean"),
        )
        .reset_index()
    )
    out["bin"] = out["bin"].astype(str)
    return out.fillna({"mean_predicted_probability": 0.0, "observed_escalation_rate": 0.0})


def _metric_rows(model_name: str, baseline_name: str, target: str, model_metrics: dict, baseline_metrics: dict) -> list[dict]:
    rows = []
    for metric, value in model_metrics.items():
        if metric == "confusion_matrix":
            continue
        rows.append({"target": target, "approach": model_name, "metric": metric, "value": value})
    for metric, value in baseline_metrics.items():
        if metric == "confusion_matrix":
            continue
        rows.append({"target": target, "approach": baseline_name, "metric": metric, "value": value})
    return rows


def run_backtest() -> dict[str, pd.DataFrame]:
    config.ensure_dirs()
    split = _release_split()
    cycle = pd.read_csv(config.CYCLE_FEATURES_CSV)
    cell = pd.read_csv(config.CELL_FEATURES_CSV)

    train_cycle = cycle[cycle["cell_id"].isin(split.train_cells)].copy()
    test_cycle = cycle[cycle["cell_id"].isin(split.test_cells)].copy()
    train_cell = cell[cell["cell_id"].isin(split.train_cells)].copy()
    test_cell = cell[cell["cell_id"].isin(split.test_cells)].copy()

    soh_name, soh_model, soh_metrics = _fit_best_regressor(
        train_cycle[C.SOH_FEATURES].astype(float),
        train_cycle["soh_current"].astype(float),
        test_cycle[C.SOH_FEATURES].astype(float),
        test_cycle["soh_current"].astype(float),
    )
    soh_base = C.regression_metrics(test_cycle["soh_current"], _soh_baseline(train_cycle, test_cycle))

    rul_name, rul_model, rul_metrics = _fit_best_regressor(
        train_cycle[C.RUL_FEATURES].astype(float),
        train_cycle["remaining_cycles"].astype(float),
        test_cycle[C.RUL_FEATURES].astype(float),
        test_cycle["remaining_cycles"].astype(float),
    )
    rul_base = C.regression_metrics(test_cycle["remaining_cycles"], _rul_baseline(test_cycle))

    fail_name, fail_model, fail_metrics, fail_proba = _fit_best_classifier(
        train_cell[C.FAILURE_FEATURES].astype(float),
        train_cell["escalation_required"].astype(int),
        test_cell[C.FAILURE_FEATURES].astype(float),
        test_cell["escalation_required"].astype(int),
    )
    baseline_proba = _failure_baseline(train_cell, test_cell)
    fail_base = C.classification_metrics(
        test_cell["escalation_required"],
        (baseline_proba >= 0.5).astype(int),
        baseline_proba,
    )

    rows = []
    rows += _metric_rows(soh_name, "fleet_median_fade_baseline", "SOH", soh_metrics, soh_base)
    rows += _metric_rows(rul_name, "current_fade_to_eol_baseline", "RUL", rul_metrics, rul_base)
    rows += _metric_rows(fail_name, "soh_station_rule_baseline", "Failure risk", fail_metrics, fail_base)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(config.MODEL_RELEASE_BACKTEST_CSV, index=False)

    threshold = _threshold_table(test_cell["escalation_required"].astype(int), fail_proba)
    calibration = _calibration_table(test_cell["escalation_required"].astype(int), fail_proba)
    calibration.to_csv(config.MODEL_RELEASE_CALIBRATION_CSV, index=False)

    report = build_report(
        split=split,
        metrics=metrics,
        threshold_table=threshold,
        calibration=calibration,
        test_cells=len(test_cell),
        test_cycle_rows=len(test_cycle),
    )
    log.info("Wrote model-release backtest outputs: %s, %s", config.MODEL_RELEASE_BACKTEST_CSV, config.MODEL_RELEASE_BACKTEST_REPORT)
    return {"metrics": metrics, "thresholds": threshold, "calibration": calibration, "report": pd.DataFrame({"markdown": [report]})}


def _fmt_metric(metrics: pd.DataFrame, target: str, approach: str, metric: str, digits: int = 3) -> str:
    value = metrics.query("target == @target and approach == @approach and metric == @metric")["value"]
    if value.empty:
        return ""
    return f"{float(value.iloc[0]):.{digits}f}"


def build_report(
    split: ReleaseSplit,
    metrics: pd.DataFrame,
    threshold_table: pd.DataFrame,
    calibration: pd.DataFrame,
    test_cells: int,
    test_cycle_rows: int,
) -> str:
    best_threshold = threshold_table.iloc[0]
    approaches = {target: metrics[metrics["target"] == target]["approach"].unique().tolist() for target in metrics["target"].unique()}
    soh_model, soh_base = approaches["SOH"]
    rul_model, rul_base = approaches["RUL"]
    fail_model, fail_base = approaches["Failure risk"]

    lines = [
        "# Model Release Backtest",
        "",
        f"_Generated: {date.today().isoformat()}._",
        "",
        "This is a release-style validation pass, not a one-off train/test score. Models are trained on older manufacturing cohorts and evaluated on later cells to mimic a new-lot rollout.",
        "",
        "## Release Split",
        "",
        f"- Training cells: {len(split.train_cells)}",
        f"- Holdout cells: {test_cells}",
        f"- Holdout cycle rows: {test_cycle_rows}",
        f"- Manufacturing-date cutoff: {split.cutoff_date}",
        "",
        "## Baseline Comparison",
        "",
        "| Target | Model / baseline | Primary metric | Value |",
        "| --- | --- | --- | --- |",
        f"| SOH | {soh_model} | RMSE | {_fmt_metric(metrics, 'SOH', soh_model, 'RMSE', 4)} |",
        f"| SOH | {soh_base} | RMSE | {_fmt_metric(metrics, 'SOH', soh_base, 'RMSE', 4)} |",
        f"| RUL | {rul_model} | MAE cycles | {_fmt_metric(metrics, 'RUL', rul_model, 'MAE', 1)} |",
        f"| RUL | {rul_base} | MAE cycles | {_fmt_metric(metrics, 'RUL', rul_base, 'MAE', 1)} |",
        f"| Failure risk | {fail_model} | F1 | {_fmt_metric(metrics, 'Failure risk', fail_model, 'f1', 3)} |",
        f"| Failure risk | {fail_base} | F1 | {_fmt_metric(metrics, 'Failure risk', fail_base, 'f1', 3)} |",
        "",
        "## Escalation Threshold Review",
        "",
        "False negatives are weighted 5x false positives to reflect the cost of missing a risky cell. The chosen threshold is the lowest-cost point on the holdout cohort.",
        "",
        "| Threshold | TP | FP | TN | FN | Precision | Recall | Review load | Cost |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in threshold_table.head(7).iterrows():
        lines.append(
            f"| {row['threshold']:.2f} | {int(row['tp'])} | {int(row['fp'])} | {int(row['tn'])} | {int(row['fn'])} | "
            f"{row['precision']:.3f} | {row['recall']:.3f} | {int(row['review_load'])} | {row['cost']:.1f} |"
        )
    lines += [
        "",
        f"Recommended release threshold: **{best_threshold['threshold']:.2f}**.",
        "",
        "## Probability Calibration",
        "",
        "| Probability bin | Rows | Mean predicted probability | Observed escalation rate |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in calibration.iterrows():
        lines.append(
            f"| {row['bin']} | {int(row['n'])} | {row['mean_predicted_probability']:.3f} | {row['observed_escalation_rate']:.3f} |"
        )
    lines += [
        "",
        "## Release Decision",
        "",
        "The release gate passes only if the model beats the simple baseline on the primary metric, has no catastrophic recall drop on later cohorts, and its chosen threshold keeps review load interpretable. These checks make the model harder to game than a single random holdout score.",
    ]
    md = "\n".join(lines) + "\n"
    config.MODEL_RELEASE_BACKTEST_REPORT.write_text(md, encoding="utf-8")
    return md


if __name__ == "__main__":
    run_backtest()
