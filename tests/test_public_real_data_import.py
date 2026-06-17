"""Tests for optional public real battery data import."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest
import scipy.io

from src.ingest.import_public_battery_data import _battery_rollup, _normalise_processed_csv
from src.ingest.nasa_mat_parser import (
    NORMALIZED_COLUMNS,
    _parse_mat_bytes,
    build_zip_index,
)


def _synthetic_nasa_mat(battery_id: str = "B9999") -> bytes:
    """Build a tiny NASA-format ``.mat`` blob (charge/discharge/impedance cycles)."""
    def cycle(ctype, cap, temps, volts, times):
        data = {
            "Voltage_measured": np.array(volts, float).reshape(1, -1),
            "Current_measured": np.zeros((1, len(times))),
            "Temperature_measured": np.array(temps, float).reshape(1, -1),
            "Current_load": np.zeros((1, len(times))),
            "Voltage_load": np.zeros((1, len(times))),
            "Time": np.array(times, float).reshape(1, -1),
        }
        if cap is not None:
            data["Capacity"] = np.array([[cap]], float)
        return {"type": ctype, "ambient_temperature": np.array([[24.0]]),
                "time": np.zeros((1, 6)), "data": data}

    cycles = [
        cycle("charge", None, [25, 30], [4.0, 4.2], [0, 100]),
        cycle("discharge", 2.0, [30, 35], [4.1, 3.0], [0, 100]),
        cycle("impedance", None, [25], [4.0], [0]),
        cycle("discharge", 1.8, [31, 36], [4.0, 2.9], [0, 100]),
        cycle("discharge", 1.5, [32, 37], [3.9, 2.8], [0, 100]),  # SOH 0.75 < 0.80
    ]
    obj = np.empty((1, len(cycles)), dtype=object)
    for i, c in enumerate(cycles):
        obj[0, i] = c
    buf = io.BytesIO()
    scipy.io.savemat(buf, {battery_id: {"cycle": obj}})
    return buf.getvalue()


# --- Official .mat archive parser ------------------------------------------
def test_parse_mat_extracts_discharge_capacity_and_soh():
    df = _parse_mat_bytes(_synthetic_nasa_mat(), "B9999")
    assert list(df.columns) == NORMALIZED_COLUMNS
    # Only discharge cycles become rows; impedance/charge are skipped.
    assert df["cycle_index"].tolist() == [0, 1, 2]
    assert df["capacity_ah"].tolist() == [2.0, 1.8, 1.5]
    assert df["soh"].round(2).tolist() == [1.0, 0.9, 0.75]
    assert df["source_adapter"].iloc[0] == "official_mat_archive"


def test_parse_mat_computes_remaining_cycles_and_charge_temp():
    df = _parse_mat_bytes(_synthetic_nasa_mat(), "B9999")
    # Remaining = discharge cycles until SOH first crosses the 80% EOL line.
    assert df["remaining_cycles"].tolist() == [2, 1, 0]
    # Charge-cycle peak temperature is attached to following discharges.
    assert df["max_charge_temp_c"].iloc[0] == pytest.approx(30.0)
    assert df["max_discharge_temp_c"].tolist() == [35.0, 36.0, 37.0]


def test_build_zip_index_is_empty_when_archive_absent(tmp_path):
    assert build_zip_index(tmp_path) == {}


def test_normalise_processed_nasa_csv(tmp_path):
    path = tmp_path / "B9999_processed.csv"
    pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2],
            "max_temp_D": [35.0, 36.0, 37.0],
            "slope_temp_D": [0.01, 0.02, 0.03],
            "slope_voltage_measured_D": [-0.001, -0.002, -0.003],
            "max_temp_C": [28.0, 29.0, 30.0],
            "capacity": [2.0, 1.8, 1.6],
            "remaining_cycles": [2, 1, 0],
        }
    ).to_csv(path, index=False)

    out = _normalise_processed_csv(path)
    assert out["battery_id"].unique().tolist() == ["B9999"]
    assert out["capacity_ah"].tolist() == [2.0, 1.8, 1.6]
    assert out["soh"].tolist() == pytest.approx([1.0, 0.9, 0.8])
    assert out["source_dataset"].iloc[0] == "NASA PCoE Battery Aging Data"


def test_battery_rollup_reports_degradation(tmp_path):
    path = tmp_path / "B9999_processed.csv"
    pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2, 3],
            "max_temp_D": [35.0, 36.0, 37.0, 38.0],
            "slope_temp_D": [0.01, 0.02, 0.03, 0.04],
            "slope_voltage_measured_D": [-0.001, -0.002, -0.003, -0.004],
            "max_temp_C": [28.0, 29.0, 30.0, 31.0],
            "capacity": [2.0, 1.7, 1.5, 1.3],
            "remaining_cycles": [3, 2, 1, 0],
        }
    ).to_csv(path, index=False)

    summary = _normalise_processed_csv(path)
    rollup = _battery_rollup(summary)
    row = rollup.iloc[0]
    assert row["cycles"] == 4
    assert row["capacity_loss_pct"] == pytest.approx(0.35)
    assert row["first_cycle_below_80pct_soh"] == 2
    assert row["capacity_cycle_corr"] < -0.9
