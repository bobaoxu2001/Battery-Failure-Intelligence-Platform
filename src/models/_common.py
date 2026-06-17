"""Shared helpers for the SOH / RUL / failure models.

Centralises feature lists, grouped train/test splitting (split by *cell* to
avoid cycle-level leakage), metrics, estimator factories (with optional
LightGBM/XGBoost), explainability (SHAP if present, else permutation
importance) and joblib persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config

# --- Feature contracts (kept explicit so leakage decisions are auditable) ---
# SOH is estimated from resistance + thermal + usage signals only; capacity-
# derived columns are intentionally excluded so the target is not leaked in.
SOH_FEATURES = [
    "cycle_count",
    "resistance_growth_rate",
    "rolling_resistance_mean_10",
    "rolling_temperature_max_10",
    "fast_charge_ratio",
    "avg_depth_of_discharge",
    "high_temp_exposure_hours",
    "batch_failure_rate",
    "station_anomaly_rate",
]

# RUL legitimately uses current health (SOH) plus degradation trend signals.
RUL_FEATURES = [
    "soh_current",
    "capacity_fade_rate",
    "resistance_growth_rate",
    "soh_delta_last_20_cycles",
    "cycle_count",
    "rolling_resistance_mean_10",
    "rolling_temperature_max_10",
    "fast_charge_ratio",
    "high_temp_exposure_hours",
    "batch_failure_rate",
    "station_anomaly_rate",
]

# Failure classifier uses lifetime engineering signals. batch_failure_rate is
# deliberately excluded (it embeds the escalation target -> leakage).
FAILURE_FEATURES = [
    "final_soh",
    "capacity_fade_rate",
    "resistance_growth_rate",
    "peak_temperature_max",
    "mean_temperature_max",
    "cycle_count",
    "fast_charge_ratio",
    "avg_depth_of_discharge",
    "high_temp_exposure_hours",
    "low_temp_exposure_hours",
    "station_anomaly_rate",
]


def has_shap() -> bool:
    try:
        import shap  # noqa: F401
        return True
    except Exception:
        return False


def boosted_regressor():
    """Return the best available gradient-boosting regressor.

    Prefers LightGBM/XGBoost when installed, otherwise scikit-learn's
    GradientBoostingRegressor. Returns ``(name, estimator)``.
    """
    try:
        from lightgbm import LGBMRegressor
        return "LightGBM", LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=config.SEED)
    except Exception:
        pass
    try:
        from xgboost import XGBRegressor
        return "XGBoost", XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=config.SEED)
    except Exception:
        pass
    return "GradientBoosting", GradientBoostingRegressor(random_state=config.SEED)


def linear_baseline() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("lr", LinearRegression())])


def random_forest_regressor() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=300, max_depth=None, min_samples_leaf=3,
                                 n_jobs=-1, random_state=config.SEED)


def logistic_baseline() -> Pipeline:
    return Pipeline([("scale", StandardScaler()),
                     ("lr", LogisticRegression(max_iter=1000, class_weight="balanced"))])


def random_forest_classifier() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=400, min_samples_leaf=2, n_jobs=-1,
                                  class_weight="balanced", random_state=config.SEED)


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def classification_metrics(y_true, y_pred, y_proba) -> dict[str, float]:
    out = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    try:
        out["roc_auc"] = float(roc_auc_score(y_true, y_proba))
    except ValueError:
        out["roc_auc"] = float("nan")
    out["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    return out


def grouped_split(frame: pd.DataFrame, features: list[str], target: str, groups: str):
    """Train/test split that keeps all rows of a given cell on one side."""
    X = frame[features].astype(float)
    y = frame[target].astype(float)
    g = frame[groups]
    splitter = GroupShuffleSplit(n_splits=1, test_size=config.TEST_SIZE, random_state=config.SEED)
    train_idx, test_idx = next(splitter.split(X, y, g))
    return (X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx])


def stratified_split(frame: pd.DataFrame, features: list[str], target: str):
    X = frame[features].astype(float)
    y = frame[target].astype(int)
    return train_test_split(X, y, test_size=config.TEST_SIZE, random_state=config.SEED, stratify=y)


def importance_table(model, X_test, y_test, features: list[str]) -> pd.DataFrame:
    """Return a feature-importance table, preferring SHAP, then permutation."""
    method = "permutation_importance"
    values = None
    if has_shap():
        try:
            import shap
            explainer = shap.Explainer(model.predict, X_test)
            shap_values = explainer(X_test)
            values = np.abs(shap_values.values).mean(axis=0)
            method = "shap_mean_abs"
        except Exception:
            values = None
    if values is None:
        result = permutation_importance(model, X_test, y_test, n_repeats=10,
                                        random_state=config.SEED, n_jobs=-1)
        values = result.importances_mean
    table = pd.DataFrame({"feature": features, "importance": values, "method": method})
    return table.sort_values("importance", ascending=False).reset_index(drop=True)


@dataclass
class ModelBundle:
    """Serialisable container for a trained model + its metadata."""
    name: str
    target: str
    features: list[str]
    estimator: object
    metrics: dict = field(default_factory=dict)
    importance: Optional[pd.DataFrame] = None
    algorithm: str = ""

    def save(self, path) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path) -> "ModelBundle":
        return joblib.load(path)


# Canonical artifact paths.
SOH_MODEL_PATH = config.MODELS_DIR / "soh_model.joblib"
RUL_MODEL_PATH = config.MODELS_DIR / "rul_model.joblib"
FAILURE_MODEL_PATH = config.MODELS_DIR / "failure_model.joblib"
