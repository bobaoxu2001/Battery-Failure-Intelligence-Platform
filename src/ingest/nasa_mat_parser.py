"""Parse the official NASA PCoE Battery Aging Data Set (raw ``.mat`` files).

This is the *authoritative* real-data adapter: it reads NASA's original MATLAB
``.mat`` archives directly (the nested ``*.zip`` files NASA ships), so the
real-data validation layer does not depend on any third-party processed mirror.

The NASA archive ships several zips, each containing a few ``B####.mat`` files.
Every ``.mat`` holds one struct (named after the battery, e.g. ``B0005``) with a
``cycle`` array. Each cycle has a ``type`` (``charge`` / ``discharge`` /
``impedance``) and a ``data`` struct of time-series measurements. Discharge
cycles carry the measured ``Capacity`` (Ah) we use to derive state-of-health.

For each battery we emit one row per *discharge* cycle in the same normalized
schema produced by the processed-CSV mirror adapter, so both sources feed the
identical downstream report:

    source_dataset, source_adapter, battery_id, cycle_index, capacity_ah, soh,
    remaining_cycles, max_discharge_temp_c, max_charge_temp_c,
    discharge_temp_slope, voltage_slope

The temperature/voltage slopes are linear fits over each discharge's own
time series, computed here from the raw signal (not copied from a mirror).

Run as a module::

    python -m src.ingest.nasa_mat_parser --battery-id B0005 --battery-id B0018
"""
from __future__ import annotations

import argparse
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

SOURCE_DATASET = "NASA PCoE Battery Aging Data"
SOURCE_ADAPTER = "official_mat_archive"

NORMALIZED_COLUMNS = [
    "source_dataset",
    "source_adapter",
    "battery_id",
    "cycle_index",
    "capacity_ah",
    "soh",
    "remaining_cycles",
    "max_discharge_temp_c",
    "max_charge_temp_c",
    "discharge_temp_slope",
    "voltage_slope",
]


@dataclass(frozen=True)
class SkippedBattery:
    battery_id: str
    reason: str


def _as_str(value) -> str:
    """Drill through nested ``.mat`` array wrappers to a scalar string."""
    arr = np.asarray(value).ravel()
    while arr.dtype == object and arr.size:
        arr = np.asarray(arr[0]).ravel()
    return str(arr[0]).strip() if arr.size else ""


def _field(rec, name: str) -> np.ndarray | None:
    """Return a 1-D numeric array for a named field of a ``.mat`` struct, or None.

    Tolerates both layouts scipy yields: a flat numeric array (NASA's real
    struct-array files) and an object-wrapped array (round-tripped fixtures).
    """
    if name not in (rec.dtype.names or ()):
        return None
    arr = np.asarray(rec[name])
    while arr.dtype == object and arr.size == 1:
        arr = np.asarray(arr.ravel()[0])
    arr = arr.ravel()
    return arr if arr.size else None


def _scalar(void, name: str) -> float:
    arr = _field(void, name)
    if arr is None:
        return float("nan")
    try:
        return float(arr[0])
    except (TypeError, ValueError):
        return float("nan")


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    """Linear slope dy/dx, robust to short/degenerate series."""
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return float("nan")
    return float(np.polyfit(x[mask], y[mask], 1)[0])


def build_zip_index(archive_dir: Path | None = None) -> dict[str, tuple[Path, str]]:
    """Map ``battery_id -> (zip_path, member_name)`` by scanning the archive zips.

    Only the zip central directories are read, so this is fast even though the
    archive is hundreds of MB on disk.
    """
    archive_dir = archive_dir or config.NASA_OFFICIAL_ARCHIVE_DIR
    index: dict[str, tuple[Path, str]] = {}
    if not archive_dir.exists():
        return index
    for zip_path in sorted(archive_dir.glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                members = zf.namelist()
        except zipfile.BadZipFile:
            log.warning("Skipping unreadable archive %s", zip_path)
            continue
        for member in members:
            name = Path(member).name
            if name.lower().endswith(".mat") and name.upper().startswith("B"):
                battery_id = name[:-4]
                index.setdefault(battery_id, (zip_path, member))
    return index


def available_batteries(archive_dir: Path | None = None) -> list[str]:
    return sorted(build_zip_index(archive_dir))


def _parse_mat_bytes(raw: bytes, battery_id: str) -> pd.DataFrame:
    """Parse a single ``.mat`` byte blob into the normalized discharge-cycle table."""
    mat = scipy.io.loadmat(io.BytesIO(raw))
    keys = [k for k in mat if not k.startswith("__")]
    if not keys:
        raise ValueError(f"{battery_id}: no battery struct found in .mat")
    struct = mat[battery_id] if battery_id in mat else mat[keys[0]]
    cycles = struct["cycle"][0, 0]

    rows = []
    discharge_index = 0
    last_charge_max_temp = float("nan")
    for i in range(cycles.shape[1]):
        cyc = cycles[0, i]
        ctype = _as_str(cyc["type"]).lower()
        if not ctype:
            continue
        data = np.asarray(cyc["data"]).reshape(-1)[0]

        if ctype == "charge":
            temp = _field(data, "Temperature_measured")
            if temp is not None:
                last_charge_max_temp = float(np.nanmax(temp))
            continue
        if ctype != "discharge":
            continue

        capacity = _field(data, "Capacity")
        if capacity is None:
            continue
        cap = float(capacity[0])
        if not np.isfinite(cap) or cap <= 0:
            continue

        temp = _field(data, "Temperature_measured")
        volt = _field(data, "Voltage_measured")
        time = _field(data, "Time")
        rows.append(
            {
                "battery_id": battery_id,
                "cycle_index": discharge_index,
                "capacity_ah": cap,
                "max_discharge_temp_c": float(np.nanmax(temp)) if temp is not None else float("nan"),
                "max_charge_temp_c": last_charge_max_temp,
                "discharge_temp_slope": _slope(time, temp) if (time is not None and temp is not None) else float("nan"),
                "voltage_slope": _slope(time, volt) if (time is not None and volt is not None) else float("nan"),
            }
        )
        discharge_index += 1

    if not rows:
        raise ValueError(f"{battery_id}: no usable discharge cycles with capacity")

    df = pd.DataFrame(rows)
    first_capacity = float(df["capacity_ah"].iloc[0])
    df["soh"] = df["capacity_ah"] / first_capacity
    df["remaining_cycles"] = _remaining_cycles(df["soh"].to_numpy())
    df["source_dataset"] = SOURCE_DATASET
    df["source_adapter"] = SOURCE_ADAPTER
    return df[NORMALIZED_COLUMNS]


def _remaining_cycles(soh: np.ndarray) -> np.ndarray:
    """Discharge cycles remaining until SOH first crosses the EOL threshold."""
    n = len(soh)
    idx = np.arange(n)
    below = np.where(soh < config.SOH_EOL_THRESHOLD)[0]
    eol = int(below[0]) if below.size else n - 1
    return np.clip(eol - idx, 0, None).astype(int)


def parse_batteries(
    battery_ids: list[str] | None = None,
    archive_dir: Path | None = None,
    all_available: bool = False,
) -> pd.DataFrame:
    """Parse the requested batteries from the official archive into one table."""
    summary, skipped = parse_batteries_detailed(battery_ids, archive_dir, all_available)
    if skipped:
        log.warning("Skipped %d requested batteries: %s", len(skipped), skipped)
    return summary


def parse_batteries_detailed(
    battery_ids: list[str] | None = None,
    archive_dir: Path | None = None,
    all_available: bool = False,
) -> tuple[pd.DataFrame, list[SkippedBattery]]:
    """Parse batteries from the official archive and return skipped-cell reasons."""
    index = build_zip_index(archive_dir)
    if not index:
        raise FileNotFoundError(
            "Official NASA archive not found. Expected battery zips under "
            f"{config.NASA_OFFICIAL_ARCHIVE_DIR}."
        )
    if all_available:
        requested = sorted(index)
    elif battery_ids:
        requested = battery_ids
    else:
        requested = [b for b in config.NASA_DEFAULT_BATTERY_IDS if b in index]
        if not requested:
            requested = sorted(index)

    frames = []
    skipped: list[SkippedBattery] = []
    for battery_id in requested:
        if battery_id not in index:
            skipped.append(SkippedBattery(battery_id, "not present in archive index"))
            continue
        zip_path, member = index[battery_id]
        try:
            with zipfile.ZipFile(zip_path) as zf:
                raw = zf.read(member)
            df = _parse_mat_bytes(raw, battery_id)
        except Exception as exc:  # noqa: BLE001 - keep other batteries parseable.
            skipped.append(SkippedBattery(battery_id, f"parse failed: {exc}"))
            log.warning("Skipping %s from %s: %s", battery_id, zip_path.name, exc)
            continue
        log.info("Parsed %s: %d discharge cycles, SOH %.3f -> %.3f (from %s)",
                 battery_id, len(df), df["soh"].iloc[0], df["soh"].iloc[-1], zip_path.name)
        frames.append(df)

    if not frames:
        detail = "; ".join(f"{item.battery_id}: {item.reason}" for item in skipped)
        raise FileNotFoundError(f"No requested batteries were parsed from the official archive. {detail}")
    return pd.concat(frames, ignore_index=True), skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse the official NASA .mat battery archive")
    parser.add_argument("--battery-id", action="append", dest="battery_ids",
                        help="battery id to parse, e.g. B0005 (repeatable)")
    parser.add_argument("--all-available", action="store_true",
                        help="parse every battery discoverable in the official archive")
    parser.add_argument("--list", action="store_true", help="list batteries discoverable in the archive")
    args = parser.parse_args()
    if args.list:
        print("\n".join(available_batteries()) or "(no archive found)")
        return
    summary = parse_batteries(args.battery_ids, all_available=args.all_available)
    summary.to_csv(config.NASA_REAL_CYCLE_SUMMARY_CSV, index=False)
    log.info("Wrote %s (%d rows, %d batteries)",
             config.NASA_REAL_CYCLE_SUMMARY_CSV, len(summary), summary["battery_id"].nunique())


if __name__ == "__main__":
    main()
