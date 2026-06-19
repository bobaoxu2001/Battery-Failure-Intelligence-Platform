"""Tests for optional public real battery data import."""
from __future__ import annotations

import io
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest
import scipy.io

from src import config
from src.ingest import import_public_battery_data
from src.ingest.import_public_battery_data import _battery_rollup, _normalise_processed_csv
from src.ingest.nasa_mat_parser import (
    NORMALIZED_COLUMNS,
    _parse_mat_bytes,
    parse_batteries_detailed,
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


def test_parse_all_available_archive_batteries(tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    with zipfile.ZipFile(archive_dir / "BatteryAgingARC_fixture.zip", "w") as zf:
        zf.writestr("nested/B9001.mat", _synthetic_nasa_mat("B9001"))
        zf.writestr("nested/B9002.mat", _synthetic_nasa_mat("B9002"))

    summary, skipped = parse_batteries_detailed(archive_dir=archive_dir, all_available=True)

    assert skipped == []
    assert summary["battery_id"].nunique() == 2
    assert set(summary["battery_id"]) == {"B9001", "B9002"}
    assert len(summary) == 6


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


def test_bundled_sample_fallback_when_archive_missing(tmp_path, monkeypatch):
    sample = tmp_path / "sample.csv"
    pd.DataFrame(
        {
            "source_dataset": ["NASA PCoE Battery Aging Data"] * 3,
            "source_adapter": ["official_mat_archive"] * 3,
            "battery_id": ["B9001"] * 3,
            "cycle_index": [0, 1, 2],
            "capacity_ah": [2.0, 1.8, 1.5],
            "soh": [1.0, 0.9, 0.75],
            "remaining_cycles": [2, 1, 0],
            "max_discharge_temp_c": [35.0, 36.0, 37.0],
            "max_charge_temp_c": [30.0, 31.0, 32.0],
            "discharge_temp_slope": [0.01, 0.02, 0.03],
            "voltage_slope": [-0.001, -0.002, -0.003],
        }
    ).to_csv(sample, index=False)
    out = tmp_path / "nasa_real_cycle_summary.csv"

    monkeypatch.setattr(config, "NASA_OFFICIAL_ARCHIVE_DIR", tmp_path / "missing_archive")
    monkeypatch.setattr(config, "NASA_PROCESSED_CSV_DIR", tmp_path / "missing_mirror")
    monkeypatch.setattr(config, "NASA_REAL_SAMPLE_CSV", sample)
    monkeypatch.setattr(config, "NASA_REAL_CYCLE_SUMMARY_CSV", out)

    summary = import_public_battery_data.build_real_cycle_summary(source="auto")

    assert out.exists()
    assert summary["battery_id"].tolist() == ["B9001", "B9001", "B9001"]
    assert summary["capacity_ah"].tolist() == [2.0, 1.8, 1.5]


def test_real_data_report_is_generated(tmp_path, monkeypatch):
    report_path = tmp_path / "real_data_validation_summary.md"
    monkeypatch.setattr(config, "REAL_DATA_VALIDATION_REPORT", report_path)
    summary = pd.DataFrame(
        {
            "source_dataset": ["NASA PCoE Battery Aging Data"] * 4,
            "source_adapter": ["official_mat_archive"] * 4,
            "battery_id": ["B9001"] * 4,
            "cycle_index": [0, 1, 2, 3],
            "capacity_ah": [2.0, 1.8, 1.5, 1.3],
            "soh": [1.0, 0.9, 0.75, 0.65],
            "remaining_cycles": [2, 1, 0, 0],
            "max_discharge_temp_c": [35.0, 36.0, 37.0, 38.0],
            "max_charge_temp_c": [30.0, 31.0, 32.0, 33.0],
            "discharge_temp_slope": [0.01, 0.02, 0.03, 0.04],
            "voltage_slope": [-0.001, -0.002, -0.003, -0.004],
        }
    )
    summary.attrs["skipped_batteries"] = [{"battery_id": "B9999", "reason": "not present in archive index"}]

    text = import_public_battery_data.build_report(summary)

    assert report_path.exists()
    assert "Number of parsed batteries: 1" in text
    assert "Temperature Summary" in text
    assert "B9999" in text


def test_import_cli_accepts_all_available_flag_with_sample_source(tmp_path, monkeypatch):
    sample = tmp_path / "sample.csv"
    pd.DataFrame(
        {
            "source_dataset": ["NASA PCoE Battery Aging Data"] * 3,
            "source_adapter": ["official_mat_archive"] * 3,
            "battery_id": ["B9001"] * 3,
            "cycle_index": [0, 1, 2],
            "capacity_ah": [2.0, 1.8, 1.5],
            "soh": [1.0, 0.9, 0.75],
            "remaining_cycles": [2, 1, 0],
            "max_discharge_temp_c": [35.0, 36.0, 37.0],
            "max_charge_temp_c": [30.0, 31.0, 32.0],
            "discharge_temp_slope": [0.01, 0.02, 0.03],
            "voltage_slope": [-0.001, -0.002, -0.003],
        }
    ).to_csv(sample, index=False)

    monkeypatch.setattr(config, "NASA_REAL_SAMPLE_CSV", sample)
    monkeypatch.setattr(config, "NASA_REAL_CYCLE_SUMMARY_CSV", tmp_path / "summary.csv")
    monkeypatch.setattr(config, "REAL_DATA_VALIDATION_REPORT", tmp_path / "report.md")
    monkeypatch.setattr(sys, "argv", ["import_public_battery_data", "--source", "sample", "--all-available"])

    import_public_battery_data.main()

    assert (tmp_path / "summary.csv").exists()
    assert (tmp_path / "report.md").exists()
