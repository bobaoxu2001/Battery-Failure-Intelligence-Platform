"""Tests for model outputs, prediction schema and escalation reporting."""
from __future__ import annotations

import pandas as pd
import pytest

from src import config
from src.models import _common as C
from src.models.score_cells import risk_tier


@pytest.fixture(scope="module")
def predictions() -> pd.DataFrame:
    return pd.read_csv(config.PREDICTIONS_CSV)


@pytest.fixture(scope="module")
def escalation() -> pd.DataFrame:
    return pd.read_csv(config.REPORTS_DIR / "escalation_report_sample.csv")


# --- Prediction schema ------------------------------------------------------
def test_prediction_columns_present(predictions):
    required = {
        "cell_id", "prediction_date", "predicted_soh", "predicted_remaining_cycles",
        "failure_probability", "risk_tier", "top_risk_driver",
    }
    assert required.issubset(predictions.columns)


def test_one_prediction_per_cell(predictions):
    assert predictions["cell_id"].is_unique


def test_no_missing_required_prediction_values(predictions):
    assert predictions.isna().sum().sum() == 0


def test_prediction_value_ranges(predictions):
    assert predictions["predicted_soh"].between(0, 1.05).all()
    assert predictions["failure_probability"].between(0, 1).all()
    assert (predictions["predicted_remaining_cycles"] >= 0).all()


def test_risk_tier_values_are_valid(predictions):
    allowed = {"Low", "Medium", "High", "Critical"}
    assert set(predictions["risk_tier"]).issubset(allowed)


# --- Risk-tier assignment logic --------------------------------------------
@pytest.mark.parametrize(
    "prob,expected",
    [(0.95, "Critical"), (0.80, "Critical"), (0.60, "High"),
     (0.55, "High"), (0.40, "Medium"), (0.30, "Medium"), (0.10, "Low"), (0.0, "Low")],
)
def test_risk_tier_thresholds(prob, expected):
    assert risk_tier(prob) == expected


def test_risk_tier_is_monotonic_in_probability(predictions):
    order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    df = predictions.sort_values("failure_probability")
    ranks = df["risk_tier"].map(order).to_numpy()
    assert all(ranks[i] <= ranks[i + 1] for i in range(len(ranks) - 1))


# --- Escalation report ------------------------------------------------------
def test_escalation_report_has_contract_columns(escalation):
    missing = [c for c in config.ESCALATION_COLUMNS if c not in escalation.columns]
    assert not missing, f"escalation report missing columns: {missing}"


def test_escalation_rows_have_root_cause_and_follow_up(escalation):
    if escalation.empty:
        pytest.skip("no cells escalated in this run")
    assert escalation["likely_root_cause"].notna().all()
    assert escalation["recommended_follow_up"].notna().all()
    assert (escalation["recommended_follow_up"].str.len() > 0).all()


# --- Trained model bundles --------------------------------------------------
def test_model_bundles_load_with_metrics():
    for path, target in [
        (C.SOH_MODEL_PATH, "soh_current"),
        (C.RUL_MODEL_PATH, "remaining_cycles"),
        (C.FAILURE_MODEL_PATH, "escalation_required"),
    ]:
        bundle = C.ModelBundle.load(path)
        assert bundle.target == target
        assert bundle.features, "bundle should record its feature list"
        assert bundle.metrics, "bundle should record its metrics"


def test_soh_features_exclude_capacity_leakage():
    # Guard: the SOH model must not train on capacity-derived columns.
    banned = {"rolling_capacity_mean_10", "capacity_fade_rate", "soh_delta_last_20_cycles", "soh_current"}
    assert not banned.intersection(C.SOH_FEATURES)


def test_failure_features_exclude_batch_failure_rate():
    # Guard against target leakage via the batch escalation rate.
    assert "batch_failure_rate" not in C.FAILURE_FEATURES
