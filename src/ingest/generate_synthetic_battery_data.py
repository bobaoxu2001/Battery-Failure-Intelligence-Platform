"""Generate realistic synthetic lithium-ion battery engineering data.

No Apple confidential data or internal systems are used anywhere in this
project. This module simulates a plausible factory + field dataset using a
physically-motivated degradation model so the rest of the platform (warehouse,
features, models, reports) has something realistic to operate on.

The simulation produces five linked tables plus a raw telemetry log:

* factory        - one row per cell (manufacturing + acceptance test metadata)
* cycles         - per-cell, per-cycle aggregated measurements (the time series)
* usage          - one row per cell (field usage profile)
* failure_events - degradation/anomaly events, incl. escalation flags
* raw log file   - free-text telemetry used to exercise the Perl/Unix ingest

Degradation realism:
* capacity fades with a slow linear region followed by an accelerating "knee",
* internal resistance grows over life and can spike for impedance-fault cells,
* lot quality, test-station calibration and field usage profile all modulate
  the fade/growth rates, which is what makes the ML models learnable.

Run as a module::

    python -m src.ingest.generate_synthetic_battery_data
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

# Field usage archetypes and how aggressively they stress the cell.
# fade_mult     -> multiplier on baseline capacity fade rate
# res_mult      -> multiplier on baseline resistance growth rate
# temp_offset_c -> mean operating-temperature offset (degC)
USAGE_PROFILES = {
    "normal": {"weight": 0.50, "fade_mult": 1.00, "res_mult": 1.00, "temp_offset_c": 0.0},
    "heavy": {"weight": 0.22, "fade_mult": 1.55, "res_mult": 1.30, "temp_offset_c": 4.0},
    "thermal_stress": {"weight": 0.16, "fade_mult": 1.95, "res_mult": 1.70, "temp_offset_c": 11.0},
    "fast_charge_heavy": {"weight": 0.12, "fade_mult": 1.70, "res_mult": 2.10, "temp_offset_c": 6.0},
}

BASE_FADE_PER_CYCLE = 0.00022      # fraction of initial capacity lost per cycle
BASE_RES_GROWTH_PER_CYCLE = 0.0011 # fractional resistance growth per cycle
KNEE_FRACTION = 0.78               # SOH level at which the degradation knee starts


def _rng() -> np.random.Generator:
    return np.random.default_rng(config.SEED)


def _assign_usage_profiles(n: int, rng: np.random.Generator) -> np.ndarray:
    names = list(USAGE_PROFILES)
    weights = np.array([USAGE_PROFILES[k]["weight"] for k in names])
    weights = weights / weights.sum()
    return rng.choice(names, size=n, p=weights)


def _build_factory(rng: np.random.Generator) -> tuple[pd.DataFrame, dict, dict]:
    """Create per-cell manufacturing metadata plus lot/station quality maps."""
    n = config.N_CELLS

    # Some lots are intrinsically lower quality (poorer materials / process).
    lot_ids = [f"LOT-{i:03d}" for i in range(1, config.N_LOTS + 1)]
    bad_lots = set(rng.choice(lot_ids, size=max(1, config.N_LOTS // 4), replace=False))
    lot_quality = {lot: (rng.uniform(1.35, 1.8) if lot in bad_lots else rng.uniform(0.9, 1.12))
                   for lot in lot_ids}

    # Some test stations are mis-calibrated, inflating measured anomalies.
    station_ids = [f"ST-{i:02d}" for i in range(1, config.N_STATIONS + 1)]
    bad_stations = set(rng.choice(station_ids, size=max(1, config.N_STATIONS // 4), replace=False))
    station_anomaly = {st: (rng.uniform(1.4, 2.0) if st in bad_stations else rng.uniform(0.85, 1.1))
                       for st in station_ids}

    equipment_ids = [f"EQ-{i:02d}" for i in range(1, config.N_EQUIPMENT + 1)]

    cell_lot = rng.choice(lot_ids, size=n)
    cell_station = rng.choice(station_ids, size=n)
    base_date = datetime(2024, 1, 1)

    rows = []
    for i in range(n):
        mfg = base_date + timedelta(days=int(rng.integers(0, 180)))
        test = mfg + timedelta(days=int(rng.integers(1, 6)))
        lot = cell_lot[i]
        rows.append(
            {
                "cell_id": f"CELL-{i + 1:05d}",
                "batch_id": f"{lot}-B{(i % 5) + 1}",
                "lot_id": lot,
                "station_id": cell_station[i],
                "test_temperature": round(float(rng.normal(25.0, 1.5)), 2),
                "charge_current": round(float(rng.choice([1.0, 1.5, 2.0])), 2),
                "discharge_current": round(float(rng.choice([1.0, 2.0, 3.0])), 2),
                "manufacturing_date": mfg.strftime("%Y-%m-%d"),
                "test_date": test.strftime("%Y-%m-%d"),
                "equipment_id": rng.choice(equipment_ids),
            }
        )
    factory = pd.DataFrame(rows)
    return factory, lot_quality, station_anomaly


def _simulate_cell_cycles(
    cell: pd.Series,
    profile: str,
    lot_quality: float,
    station_anomaly: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Simulate the per-cycle measurement time series for a single cell."""
    prof = USAGE_PROFILES[profile]
    life = int(rng.integers(config.MIN_LIFE_CYCLES, config.MAX_LIFE_CYCLES + 1))

    init_cap = config.NOMINAL_CAPACITY_AH * float(rng.normal(1.0, 0.015))
    init_res = config.NOMINAL_RESISTANCE_MOHM * float(rng.normal(1.0, 0.05))

    fade_rate = BASE_FADE_PER_CYCLE * prof["fade_mult"] * lot_quality * float(rng.normal(1.0, 0.08))
    res_growth = BASE_RES_GROWTH_PER_CYCLE * prof["res_mult"] * lot_quality * float(rng.normal(1.0, 0.1))

    cycles = np.arange(1, life + 1)

    # Linear fade plus an accelerating knee once degradation is advanced.
    linear_soh = 1.0 - fade_rate * cycles
    knee_excess = np.clip(KNEE_FRACTION - linear_soh, 0, None)
    soh = linear_soh - 2.6 * knee_excess ** 2
    soh += rng.normal(0, 0.0035, size=life)  # measurement noise
    soh = np.clip(soh, 0.45, 1.02)

    discharge_cap = soh * init_cap
    charge_cap = discharge_cap * rng.normal(1.012, 0.004, size=life)

    # Resistance grows over life; accelerates as the cell ages.
    resistance = init_res * (1.0 + res_growth * cycles + 0.45 * (res_growth * cycles) ** 2)
    resistance += rng.normal(0, 0.25, size=life)

    # Inject an impedance fault on a minority of stressed cells.
    impedance_fault = (profile == "fast_charge_heavy") and (rng.random() < 0.30)
    fault_cycle = None
    if impedance_fault:
        fault_cycle = int(rng.integers(int(0.5 * life), life))
        resistance[fault_cycle:] *= rng.uniform(1.25, 1.55)

    op_temp = 24.0 + prof["temp_offset_c"]
    temp_mean = rng.normal(op_temp, 1.2, size=life) + 0.012 * cycles  # warms slightly with age
    temp_max = temp_mean + np.abs(rng.normal(6.0, 1.5, size=life)) * station_anomaly

    voltage_mean = rng.normal(3.68, 0.02, size=life)
    voltage_min = voltage_mean - np.abs(rng.normal(0.55, 0.05, size=life))
    voltage_max = voltage_mean + np.abs(rng.normal(0.45, 0.04, size=life))
    current_mean = -np.abs(rng.normal(float(cell["discharge_current"]), 0.05, size=life))

    energy = discharge_cap * config.NOMINAL_VOLTAGE_V

    test_start = datetime.strptime(cell["test_date"], "%Y-%m-%d")
    timestamps = [(test_start + timedelta(hours=2 * int(c))).strftime("%Y-%m-%dT%H:%M:%SZ") for c in cycles]

    frame = pd.DataFrame(
        {
            "cell_id": cell["cell_id"],
            "cycle_index": cycles,
            "voltage_mean": np.round(voltage_mean, 4),
            "voltage_min": np.round(voltage_min, 4),
            "voltage_max": np.round(voltage_max, 4),
            "current_mean": np.round(current_mean, 4),
            "temperature_mean": np.round(temp_mean, 3),
            "temperature_max": np.round(temp_max, 3),
            "discharge_capacity_ah": np.round(discharge_cap, 5),
            "charge_capacity_ah": np.round(charge_cap, 5),
            "internal_resistance_mohm": np.round(resistance, 4),
            "energy_wh": np.round(energy, 4),
            "timestamp": timestamps,
        }
    )
    frame.attrs["init_cap"] = init_cap
    frame.attrs["init_res"] = init_res
    frame.attrs["soh"] = soh
    frame.attrs["fault_cycle"] = fault_cycle
    return frame


def _build_usage(factory: pd.DataFrame, profiles: dict[str, str], rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for _, cell in factory.iterrows():
        profile = profiles[cell["cell_id"]]
        prof = USAGE_PROFILES[profile]
        fast_charge = {
            "normal": rng.uniform(0.05, 0.20),
            "heavy": rng.uniform(0.20, 0.45),
            "thermal_stress": rng.uniform(0.15, 0.40),
            "fast_charge_heavy": rng.uniform(0.55, 0.85),
        }[profile]
        rows.append(
            {
                "cell_id": cell["cell_id"],
                "avg_depth_of_discharge": round(float(rng.uniform(0.55, 0.95)), 3),
                "fast_charge_ratio": round(float(fast_charge), 3),
                "avg_daily_cycles": round(float(rng.uniform(0.8, 2.6)), 2),
                "high_temp_exposure_hours": round(float(rng.uniform(20, 120) * (1 + prof["temp_offset_c"] / 10)), 1),
                "low_temp_exposure_hours": round(float(rng.uniform(5, 60)), 1),
                "usage_profile": profile,
            }
        )
    return pd.DataFrame(rows)


def _build_failure_events(
    factory: pd.DataFrame,
    cycle_meta: dict[str, dict],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Derive degradation/anomaly events and escalation decisions per cell."""
    rows = []
    for _, cell in factory.iterrows():
        cid = cell["cell_id"]
        meta = cycle_meta[cid]
        soh = meta["soh"]
        final_soh = float(soh[-1])
        life = len(soh)

        # End-of-life cycle (first crossing below the EOL threshold), if reached.
        below = np.where(soh < config.SOH_EOL_THRESHOLD)[0]
        eol_cycle = int(below[0] + 1) if below.size else None

        # Early degradation: fell under the "early" SOH unusually fast.
        early_idx = np.where(soh < config.EARLY_DEGRADATION_SOH)[0]
        early_cycle = int(early_idx[0] + 1) if early_idx.size else life
        early_degradation = bool(early_cycle < 0.35 * config.MAX_LIFE_CYCLES and final_soh < 0.9)

        # Sudden capacity drop event (large cycle-over-cycle loss anywhere).
        drops = np.diff(soh)
        capacity_drop = bool(drops.min() < -0.02)

        impedance_spike = meta["fault_cycle"] is not None
        thermal_anomaly = bool(meta["temp_max_peak"] > 48.0)

        severity_score = (
            (1 - final_soh) * 3.0
            + 1.2 * early_degradation
            + 0.9 * capacity_drop
            + 1.1 * impedance_spike
            + 0.8 * thermal_anomaly
        )
        if severity_score >= 2.4:
            severity = "critical"
        elif severity_score >= 1.6:
            severity = "high"
        elif severity_score >= 0.9:
            severity = "medium"
        else:
            severity = "low"

        escalation = bool(severity in ("high", "critical") and (early_degradation or impedance_spike or eol_cycle))

        # Pick a representative event type for the row.
        if impedance_spike:
            event_type = "impedance_growth"
        elif thermal_anomaly:
            event_type = "thermal_event"
        elif early_degradation:
            event_type = "early_degradation"
        elif capacity_drop:
            event_type = "capacity_drop"
        else:
            event_type = "nominal_fade"

        test_start = datetime.strptime(cell["test_date"], "%Y-%m-%d")
        event_cycle = eol_cycle or early_cycle
        event_date = (test_start + timedelta(hours=2 * event_cycle)).strftime("%Y-%m-%d")

        rows.append(
            {
                "cell_id": cid,
                "event_date": event_date,
                "event_type": event_type,
                "capacity_drop_event": int(capacity_drop),
                "impedance_spike_event": int(impedance_spike),
                "thermal_anomaly_event": int(thermal_anomaly),
                "early_degradation_flag": int(early_degradation),
                "escalation_required": int(escalation),
                "failure_severity": severity,
            }
        )
    return pd.DataFrame(rows)


def _write_raw_log(factory: pd.DataFrame, cycles: pd.DataFrame, rng: np.random.Generator) -> None:
    """Emit a free-text telemetry log (with some malformed lines) for Perl ingest."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    sample_cells = factory["cell_id"].sample(min(15, len(factory)), random_state=config.SEED).tolist()
    station_map = factory.set_index("cell_id")["station_id"].to_dict()
    sub = cycles[cycles["cell_id"].isin(sample_cells)].groupby("cell_id").head(40)

    lines = ["# RAW BATTERY CYCLER TELEMETRY EXPORT (synthetic)",
             "# format: <iso8601> | STATION=<id> | CELL=<id> | V=<volt> | I=<amp> | T=<degC>"]
    for _, r in sub.iterrows():
        line = (
            f"{r['timestamp']} | STATION={station_map[r['cell_id']]} | CELL={r['cell_id']} "
            f"| V={r['voltage_mean']:.3f} | I={r['current_mean']:.3f} | T={r['temperature_mean']:.2f}"
        )
        # Inject ~4% malformed rows to exercise the parser's error handling.
        if rng.random() < 0.04:
            line = line.replace("V=", "V=NaN_").split("| T=")[0]
        lines.append(line)
    config.RAW_LOG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote raw telemetry log: %s (%d lines)", config.RAW_LOG_FILE, len(lines))


def generate() -> dict[str, pd.DataFrame]:
    """Generate all synthetic tables and persist them under ``data/synthetic``."""
    config.ensure_dirs()
    rng = _rng()
    log.info("Generating synthetic battery data | cells=%d quick=%s", config.N_CELLS, config.QUICK_MODE)

    factory, lot_quality, station_anomaly = _build_factory(rng)
    profiles = dict(zip(factory["cell_id"], _assign_usage_profiles(len(factory), rng)))

    cycle_frames = []
    cycle_meta: dict[str, dict] = {}
    for _, cell in factory.iterrows():
        profile = profiles[cell["cell_id"]]
        frame = _simulate_cell_cycles(
            cell, profile, lot_quality[cell["lot_id"]], station_anomaly[cell["station_id"]], rng
        )
        cycle_frames.append(frame.drop(columns=[]))
        cycle_meta[cell["cell_id"]] = {
            "soh": frame.attrs["soh"],
            "fault_cycle": frame.attrs["fault_cycle"],
            "temp_max_peak": float(frame["temperature_max"].max()),
        }
    cycles = pd.concat(cycle_frames, ignore_index=True)

    usage = _build_usage(factory, profiles, rng)
    failures = _build_failure_events(factory, cycle_meta, rng)

    # Persist to the "synthetic" landing zone (raw-ish source of truth).
    config.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    factory.to_csv(config.SYNTHETIC_DIR / "factory.csv", index=False)
    cycles.to_csv(config.SYNTHETIC_DIR / "cycles.csv", index=False)
    usage.to_csv(config.SYNTHETIC_DIR / "usage.csv", index=False)
    failures.to_csv(config.SYNTHETIC_DIR / "failure_events.csv", index=False)
    _write_raw_log(factory, cycles, rng)

    log.info(
        "Generated: factory=%d cycles=%d usage=%d failures=%d (escalations=%d)",
        len(factory), len(cycles), len(usage), len(failures), int(failures["escalation_required"].sum()),
    )
    return {"factory": factory, "cycles": cycles, "usage": usage, "failure_events": failures}


if __name__ == "__main__":
    generate()
