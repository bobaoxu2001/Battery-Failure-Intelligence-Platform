"""Tests for the feature-engineering layer."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config
from src.features.build_features import (
    CELL_FEATURE_COLUMNS,
    CYCLE_FEATURE_COLUMNS,
    EARLY_WARNING_FEATURE_COLUMNS,
    _initial_capacity,
    _leave_one_out_group_rate,
    _remaining_cycles,
)


@pytest.fixture(scope="module")
def cycle_features() -> pd.DataFrame:
    return pd.read_csv(config.CYCLE_FEATURES_CSV)


@pytest.fixture(scope="module")
def cell_features() -> pd.DataFrame:
    return pd.read_csv(config.CELL_FEATURES_CSV)


@pytest.fixture(scope="module")
def early_warning_features() -> pd.DataFrame:
    return pd.read_csv(config.EARLY_WARNING_FEATURES_CSV)


def test_cycle_features_have_required_columns(cycle_features):
    missing = [c for c in CYCLE_FEATURE_COLUMNS if c not in cycle_features.columns]
    assert not missing, f"cycle_features missing columns: {missing}"


def test_cell_features_have_required_columns(cell_features):
    missing = [c for c in CELL_FEATURE_COLUMNS if c not in cell_features.columns]
    assert not missing, f"cell_features missing columns: {missing}"


def test_early_warning_features_have_required_columns(early_warning_features):
    missing = [c for c in EARLY_WARNING_FEATURE_COLUMNS if c not in early_warning_features.columns]
    assert not missing, f"early_warning_features missing columns: {missing}"


def test_early_warning_features_exclude_lifetime_leakage_columns(early_warning_features):
    banned = {
        "final_soh",
        "cycle_count",
        "peak_temperature_max",
        "mean_temperature_max",
        "capacity_fade_rate",
        "resistance_growth_rate",
        "batch_failure_rate",
    }
    assert not banned.intersection(early_warning_features.columns)


def test_early_warning_features_one_row_per_cell(early_warning_features):
    assert early_warning_features["cell_id"].is_unique
    assert (early_warning_features["early_cycle_count"] <= 50).all()


def test_no_missing_values_in_key_columns(cycle_features):
    key = ["cell_id", "cycle_index", "soh_current", "remaining_cycles"]
    assert cycle_features[key].isna().sum().sum() == 0


def test_soh_in_plausible_range(cycle_features):
    soh = cycle_features["soh_current"]
    assert soh.between(0.3, 1.1).all(), "SOH outside plausible physical band"


def test_remaining_cycles_non_negative(cycle_features):
    assert (cycle_features["remaining_cycles"] >= 0).all()


def test_one_feature_row_per_cell_cycle(cycle_features):
    dupes = cycle_features.duplicated(subset=["cell_id", "cycle_index"]).sum()
    assert dupes == 0, "duplicate (cell_id, cycle_index) feature rows"


def test_cell_features_one_row_per_cell(cell_features):
    assert cell_features["cell_id"].is_unique


def test_group_rates_exclude_current_cell_target():
    frame = pd.DataFrame(
        {
            "cell_id": ["A", "B", "C", "D"],
            "batch_id": ["LOT-1", "LOT-1", "LOT-1", "LOT-2"],
            "escalation_required": [1, 0, 0, 1],
        }
    )
    rates = _leave_one_out_group_rate(frame, "batch_id", "escalation_required")
    assert rates["A"] == pytest.approx(0.0)
    assert rates["B"] == pytest.approx(0.5)
    assert rates["C"] == pytest.approx(0.5)
    # Singleton group falls back to fleet leave-one-out, excluding D itself.
    assert rates["D"] == pytest.approx(1 / 3)


# --- Unit tests of the pure helpers ----------------------------------------
def test_initial_capacity_is_mean_of_first_cycles():
    g = pd.DataFrame({"cycle_index": range(1, 11),
                      "discharge_capacity_ah": [3.5, 3.5, 3.5, 3.4, 3.4, 3.3, 3.2, 3.1, 3.0, 2.9]})
    # mean of first 5 = (3.5+3.5+3.5+3.4+3.4)/5 = 3.46
    assert _initial_capacity(g) == pytest.approx(3.46, abs=1e-6)


def test_remaining_cycles_uses_actual_eol_crossing():
    cycle_index = np.arange(1, 11)
    soh = np.linspace(1.0, 0.7, 10)  # crosses 0.80 somewhere in the series
    remaining = _remaining_cycles(soh, cycle_index)
    eol_idx = np.where(soh < config.SOH_EOL_THRESHOLD)[0][0]
    eol_cycle = cycle_index[eol_idx]
    # At cycle 1, remaining should equal eol_cycle - 1.
    assert remaining[0] == pytest.approx(eol_cycle - 1)
    # Monotonically non-increasing and clipped at zero.
    assert (np.diff(remaining) <= 1e-9).all()
    assert remaining.min() >= 0


def test_remaining_cycles_extrapolates_when_no_eol():
    cycle_index = np.arange(1, 21)
    soh = np.linspace(1.0, 0.92, 20)  # never reaches 0.80 -> must extrapolate
    remaining = _remaining_cycles(soh, cycle_index)
    assert remaining[-1] > 0, "should project a positive remaining life"
