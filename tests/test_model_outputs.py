"""Tests for model outputs, prediction schema and escalation reporting."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from src import config
from src.models.monitor_drift import population_stability_index, psi_status
from src.models import _common as C
from src.models.score_cells import risk_tier
from src.models.train_survival_rul_model import SurvivalBundle
from src.reporting.generate_jmp_exports import JMP_COLUMNS


@pytest.fixture(scope="module")
def predictions() -> pd.DataFrame:
    return pd.read_csv(config.PREDICTIONS_CSV)


@pytest.fixture(scope="module")
def escalation() -> pd.DataFrame:
    return pd.read_csv(config.REPORTS_DIR / "escalation_report_sample.csv")


@pytest.fixture(scope="module")
def jmp_export() -> pd.DataFrame:
    return pd.read_csv(config.JMP_ANALYSIS_CSV)


@pytest.fixture(scope="module")
def monitoring_metrics() -> pd.DataFrame:
    return pd.read_csv(config.MODEL_MONITORING_METRICS_CSV)


@pytest.fixture(scope="module")
def release_metrics() -> pd.DataFrame:
    return pd.read_csv(config.MODEL_RELEASE_BACKTEST_CSV)


@pytest.fixture(scope="module")
def release_calibration() -> pd.DataFrame:
    return pd.read_csv(config.MODEL_RELEASE_CALIBRATION_CSV)


@pytest.fixture(scope="module")
def survival_predictions() -> pd.DataFrame:
    return pd.read_csv(config.SURVIVAL_PREDICTIONS_CSV)


# --- Prediction schema ------------------------------------------------------
def test_prediction_columns_present(predictions):
    required = {
        "cell_id", "prediction_date", "predicted_soh", "predicted_remaining_cycles",
        "failure_probability", "risk_tier", "early_warning_probability",
        "early_warning_risk_tier", "top_risk_driver",
    }
    assert required.issubset(predictions.columns)


def test_one_prediction_per_cell(predictions):
    assert predictions["cell_id"].is_unique


def test_no_missing_required_prediction_values(predictions):
    assert predictions.isna().sum().sum() == 0


def test_prediction_value_ranges(predictions):
    assert predictions["predicted_soh"].between(0, 1.05).all()
    assert predictions["failure_probability"].between(0, 1).all()
    assert predictions["early_warning_probability"].between(0, 1).all()
    assert (predictions["predicted_remaining_cycles"] >= 0).all()


def test_risk_tier_values_are_valid(predictions):
    allowed = {"Low", "Medium", "High", "Critical"}
    assert set(predictions["risk_tier"]).issubset(allowed)
    assert set(predictions["early_warning_risk_tier"]).issubset(allowed)


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


def test_escalation_summary_counts_reconcile(escalation):
    """Guard: the headline total must equal the sum of the per-tier breakdown.

    Regression test for the count mismatch where the headline said "32 cells"
    but only listed 24 Critical + 7 High (the Medium rule-based escalation was
    hidden). The displayed total, the composition table, the Total row, and the
    actual queue length must all agree.
    """
    text = (config.REPORTS_DIR / "high_risk_cells_summary.md").read_text(encoding="utf-8")

    headline = re.search(r"\*\*(\d+) cells\*\* require engineering attention", text)
    assert headline, "could not find the headline total in the summary"
    headline_total = int(headline.group(1))

    tier_counts = {}
    for tier in ("Critical", "High", "Medium", "Low"):
        row = re.search(rf"^\|\s*{tier}\s*\|\s*(\d+)\s*\|", text, re.MULTILINE)
        assert row, f"composition table is missing the {tier} row"
        tier_counts[tier] = int(row.group(1))

    total_row = re.search(r"\|\s*\*\*Total\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|", text)
    assert total_row, "composition table is missing the Total row"

    assert sum(tier_counts.values()) == headline_total, (
        f"tier counts {tier_counts} sum to {sum(tier_counts.values())} "
        f"but headline says {headline_total}"
    )
    assert int(total_row.group(1)) == headline_total
    # The displayed total must also match the actual machine-readable queue.
    assert headline_total == len(escalation)


# --- JMP / monitoring outputs ----------------------------------------------
def test_jmp_export_has_expected_analysis_columns(jmp_export):
    missing = [c for c in JMP_COLUMNS if c not in jmp_export.columns]
    assert not missing, f"JMP export missing columns: {missing}"
    assert jmp_export["cell_id"].is_unique


def test_jmp_script_references_export_and_analysis_platforms():
    text = config.JMP_SCRIPT.read_text(encoding="utf-8")
    assert "jmp_cell_analysis.csv" in text
    assert "Distribution(" in text
    assert "Fit Model(" in text


def test_monitoring_metrics_have_psi_status(monitoring_metrics):
    required = {"feature", "reference_mean", "current_mean", "delta", "psi", "status"}
    assert required.issubset(monitoring_metrics.columns)
    assert monitoring_metrics["status"].isin({"ok", "watch", "alert", "unknown"}).all()


def test_model_release_backtest_compares_models_to_baselines(release_metrics):
    required_targets = {"SOH", "RUL", "Failure risk"}
    assert required_targets.issubset(set(release_metrics["target"]))
    approaches = set(release_metrics["approach"])
    assert "fleet_median_fade_baseline" in approaches
    assert "current_fade_to_eol_baseline" in approaches
    assert "soh_station_rule_baseline" in approaches
    assert release_metrics["value"].notna().all()


def test_model_release_report_has_threshold_and_calibration_context(release_calibration):
    text = config.MODEL_RELEASE_BACKTEST_REPORT.read_text(encoding="utf-8")
    assert "Escalation Threshold Review" in text
    assert "Probability Calibration" in text
    assert "Recommended release threshold" in text
    required = {"bin", "n", "mean_predicted_probability", "observed_escalation_rate"}
    assert required.issubset(release_calibration.columns)
    assert release_calibration["n"].sum() > 0


def test_early_warning_report_documents_feature_boundary():
    text = config.EARLY_WARNING_REPORT.read_text(encoding="utf-8")
    assert "first 50 cycles" in text
    assert "Excluded" in text
    assert "final_soh" in text
    assert "retrospective investigation model" in text


def test_survival_rul_outputs_capture_censoring(survival_predictions):
    required = {
        "cell_id",
        "event_observed",
        "observed_duration_cycles",
        "predicted_expected_eol_cycle",
        "predicted_remaining_cycles_from_observed",
        "event_probability_by_500_cycles",
    }
    assert required.issubset(survival_predictions.columns)
    assert set(survival_predictions["event_observed"].unique()).issubset({0, 1})
    assert survival_predictions["event_observed"].isin([0]).any(), "holdout should include censored cells"
    assert survival_predictions["event_probability_by_500_cycles"].between(0, 1).all()


def test_survival_model_bundle_loads_with_metrics():
    bundle = SurvivalBundle.load()
    assert "concordance_index" in bundle.metrics
    assert bundle.interval_width > 0
    assert "log_interval_end" in bundle.features


def test_project_readiness_scorecard_is_complete():
    text = config.PROJECT_READINESS_SCORECARD.read_text(encoding="utf-8")
    assert "Overall Score: 13/13" in text
    assert "Verdict: **portfolio-ready**" in text
    assert "MISSING" not in text


def test_hiring_manager_packet_has_fast_review_evidence():
    text = config.HIRING_MANAGER_PACKET.read_text(encoding="utf-8")
    assert "First 60 Seconds" in text
    assert "reports/cell_investigation_case_study.md" in text
    assert "reports/real_data_validation_summary.md" in text
    assert "| Proof point | Artifact | Why it matters | Status |" in text
    assert "missing" not in text.lower()


def test_cell_investigation_case_study_has_decision_context():
    text = config.CELL_INVESTIGATION_CASE_STUDY.read_text(encoding="utf-8")
    assert "Selected Cell" in text
    assert "Peer Context" in text
    assert "Decision" in text
    assert "synthetic production-style investigation" in text


def test_population_stability_index_status_thresholds():
    ref = pd.Series([0, 1, 2, 3, 4, 5])
    cur = pd.Series([0, 1, 2, 3, 4, 5])
    assert population_stability_index(ref, cur) == pytest.approx(0.0)
    assert psi_status(0.05) == "ok"
    assert psi_status(0.12) == "watch"
    assert psi_status(0.30) == "alert"


# --- Trained model bundles --------------------------------------------------
def test_model_bundles_load_with_metrics():
    for path, target in [
        (C.SOH_MODEL_PATH, "soh_current"),
        (C.RUL_MODEL_PATH, "remaining_cycles"),
        (C.FAILURE_MODEL_PATH, "escalation_required"),
        (C.EARLY_WARNING_MODEL_PATH, "escalation_required"),
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


def test_early_warning_features_exclude_lifetime_leakage():
    banned = {
        "final_soh",
        "cycle_count",
        "peak_temperature_max",
        "mean_temperature_max",
        "capacity_fade_rate",
        "resistance_growth_rate",
        "batch_failure_rate",
    }
    assert not banned.intersection(C.EARLY_WARNING_FEATURES)
