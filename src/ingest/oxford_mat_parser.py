"""Parser for the Oxford Battery Degradation Dataset 1 ``.mat`` files.

The full Oxford archive contains Cell1..Cell8 structs, each with snapshots like
``cyc0000`` and ``cyc0100``. Each snapshot stores C1 charge/discharge and OCV
sub-structs. For cross-dataset validation we normalize the C1 discharge series
to one row per cell x snapshot with capacity, SOH, temperature, and voltage
summary fields.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

OXFORD_DATASET_NAME = "Oxford Battery Degradation Dataset 1"
OXFORD_OFFICIAL_URL = "https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac"
OXFORD_DOI = "10.5287/bodleian:KO2kdmYGg"


def _as_array(value) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _cycle_number(name: str) -> int | None:
    match = re.fullmatch(r"cyc(\d+)", name)
    return int(match.group(1)) if match else None


def _capacity_ah(discharge) -> float:
    q = _as_array(discharge.q)
    if q.size == 0:
        return float("nan")
    # Oxford stores C1 discharge capacity in mAh-like units with negative sign.
    return float(abs(np.nanmin(q)) / 1000.0)


def _snapshot_row(cell_name: str, cycle_name: str, snapshot) -> dict | None:
    if not hasattr(snapshot, "C1dc"):
        return None
    discharge = snapshot.C1dc
    if not all(hasattr(discharge, attr) for attr in ("q", "T", "v")):
        return None
    cycle_index = _cycle_number(cycle_name)
    if cycle_index is None:
        return None
    temp = _as_array(discharge.T)
    volt = _as_array(discharge.v)
    capacity = _capacity_ah(discharge)
    return {
        "source_dataset": OXFORD_DATASET_NAME,
        "source_adapter": "official_mat_archive",
        "cell_id": cell_name,
        "cycle_index": cycle_index,
        "capacity_ah": capacity,
        "max_discharge_temp_c": float(np.nanmax(temp)) if temp.size else np.nan,
        "mean_discharge_temp_c": float(np.nanmean(temp)) if temp.size else np.nan,
        "min_voltage_v": float(np.nanmin(volt)) if volt.size else np.nan,
        "max_voltage_v": float(np.nanmax(volt)) if volt.size else np.nan,
        "n_discharge_points": int(len(temp)),
    }


def parse_oxford_mat(path: Path) -> pd.DataFrame:
    """Parse an Oxford ``.mat`` file into a normalized cycle summary."""
    mat = loadmat(path, squeeze_me=True, struct_as_record=False)
    rows: list[dict] = []

    # Full archive: Cell1..Cell8. Example file: ExampleDC_C1 with one ch/dc pair.
    full_cells = [key for key in mat.keys() if re.fullmatch(r"Cell\d+", key)]
    if full_cells:
        for cell_name in sorted(full_cells, key=lambda x: int(x.replace("Cell", ""))):
            cell = mat[cell_name]
            for cycle_name in sorted(cell._fieldnames, key=lambda x: _cycle_number(x) or -1):
                row = _snapshot_row(cell_name, cycle_name, getattr(cell, cycle_name))
                if row:
                    rows.append(row)
    elif "ExampleDC_C1" in mat:
        example = mat["ExampleDC_C1"]
        if hasattr(example, "dc"):
            temp = _as_array(example.dc.T)
            volt = _as_array(example.dc.v)
            capacity = _capacity_ah(example.dc)
            rows.append(
                {
                    "source_dataset": OXFORD_DATASET_NAME,
                    "source_adapter": "official_example_mat",
                    "cell_id": "ExampleDC_C1",
                    "cycle_index": 0,
                    "capacity_ah": capacity,
                    "max_discharge_temp_c": float(np.nanmax(temp)) if temp.size else np.nan,
                    "mean_discharge_temp_c": float(np.nanmean(temp)) if temp.size else np.nan,
                    "min_voltage_v": float(np.nanmin(volt)) if volt.size else np.nan,
                    "max_voltage_v": float(np.nanmax(volt)) if volt.size else np.nan,
                    "n_discharge_points": int(len(temp)),
                }
            )

    if not rows:
        raise ValueError(f"No Oxford battery cycle snapshots parsed from {path}")

    frame = pd.DataFrame(rows).dropna(subset=["capacity_ah", "cycle_index"])
    frame = frame.sort_values(["cell_id", "cycle_index"]).reset_index(drop=True)
    first_capacity = frame.groupby("cell_id")["capacity_ah"].transform("first")
    frame["soh"] = frame["capacity_ah"] / first_capacity
    return frame


def battery_rollup(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cell_id, group in summary.groupby("cell_id"):
        group = group.sort_values("cycle_index")
        initial = float(group["capacity_ah"].iloc[0])
        final = float(group["capacity_ah"].iloc[-1])
        corr = float(np.corrcoef(group["cycle_index"], group["capacity_ah"])[0, 1]) if len(group) > 2 else np.nan
        below_80 = group[group["soh"] < 0.80]
        rows.append(
            {
                "cell_id": cell_id,
                "snapshots": int(len(group)),
                "first_cycle_index": int(group["cycle_index"].min()),
                "last_cycle_index": int(group["cycle_index"].max()),
                "initial_capacity_ah": initial,
                "final_capacity_ah": final,
                "capacity_loss_pct": (initial - final) / initial if initial else np.nan,
                "first_cycle_below_80pct_soh": int(below_80["cycle_index"].iloc[0]) if not below_80.empty else None,
                "max_discharge_temp_c": float(group["max_discharge_temp_c"].max()),
                "capacity_cycle_corr": corr,
            }
        )
    return pd.DataFrame(rows).sort_values("cell_id").reset_index(drop=True)
