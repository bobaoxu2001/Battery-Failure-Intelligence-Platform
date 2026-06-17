"""Engineer modeling features from the processed battery tables.

Two feature tables are produced:

``cycle_features`` (one row per cell x cycle)
    Trend/rolling features used by the SOH (state-of-health) and RUL
    (remaining-useful-life) regressors. Targets:
      * ``soh_current``      = discharge_capacity / initial_capacity
      * ``remaining_cycles`` = cycles until SOH crosses the EOL threshold
        (extrapolated for cells that never reach EOL within their recorded life)

``cell_features`` (one row per cell)
    Aggregated lifetime features used by the failure-risk classifier. Target:
      * ``escalation_required`` (engineering escalation needed)

Run as a module::

    python -m src.features.build_features
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.utils.logging_utils import get_logger, log_dataframe

log = get_logger(__name__)

# Feature columns the downstream models rely on (kept explicit for the tests).
CYCLE_FEATURE_COLUMNS = [
    "cycle_count",
    "soh_current",
    "capacity_fade_rate",
    "resistance_growth_rate",
    "rolling_capacity_mean_10",
    "rolling_temperature_max_10",
    "rolling_resistance_mean_10",
    "soh_delta_last_20_cycles",
    "fast_charge_ratio",
    "avg_depth_of_discharge",
    "high_temp_exposure_hours",
    "batch_failure_rate",
    "station_anomaly_rate",
]

CELL_FEATURE_COLUMNS = [
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
    "batch_failure_rate",
    "station_anomaly_rate",
]


def _read_processed() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factory = pd.read_csv(config.FACTORY_CSV)
    cycles = pd.read_csv(config.CYCLES_CSV)
    usage = pd.read_csv(config.USAGE_CSV)
    failures = pd.read_csv(config.FAILURES_CSV)
    return factory, cycles, usage, failures


def _initial_capacity(group: pd.DataFrame) -> float:
    """Robust initial capacity = mean of the first few cycles."""
    head = group.sort_values("cycle_index").head(5)
    return float(head["discharge_capacity_ah"].mean())


def _remaining_cycles(soh: np.ndarray, cycle_index: np.ndarray) -> np.ndarray:
    """Cycles remaining until SOH < EOL threshold for each point in the series.

    If the cell reaches end-of-life within its recorded life we use the actual
    crossing cycle. Otherwise we linearly extrapolate the recent fade trend to
    project the crossing (a common, defensible RUL estimate).
    """
    thr = config.SOH_EOL_THRESHOLD
    below = np.where(soh < thr)[0]
    if below.size:
        eol_cycle = cycle_index[below[0]]
    else:
        # Project EOL from the slope over the last quarter of life.
        n = len(soh)
        lo = max(1, int(0.75 * n))
        x, y = cycle_index[lo - 1:], soh[lo - 1:]
        slope = np.polyfit(x, y, 1)[0] if len(x) > 2 else -1e-6
        slope = min(slope, -1e-6)  # guard against flat/positive slope
        eol_cycle = cycle_index[-1] + (thr - soh[-1]) / slope
    remaining = np.clip(eol_cycle - cycle_index, 0, None)
    return remaining


def _leave_one_out_group_rate(
    frame: pd.DataFrame,
    group_col: str,
    value_col: str,
    id_col: str = "cell_id",
) -> dict[str, float]:
    """Return per-row group rates excluding that row's own target value.

    Batch/station rates are useful manufacturing context, but a cell should not
    get to encode its own escalation/anomaly label into its feature row.
    Singleton groups fall back to the fleet leave-one-out rate.
    """
    total_sum = float(frame[value_col].sum())
    total_count = int(frame[value_col].count())
    stats = frame.groupby(group_col)[value_col].agg(["sum", "count"])

    rates: dict[str, float] = {}
    for row in frame[[id_col, group_col, value_col]].itertuples(index=False):
        group = getattr(row, group_col)
        own_value = float(getattr(row, value_col))
        group_sum = float(stats.loc[group, "sum"])
        group_count = int(stats.loc[group, "count"])
        if group_count > 1:
            rates[getattr(row, id_col)] = (group_sum - own_value) / (group_count - 1)
        elif total_count > 1:
            rates[getattr(row, id_col)] = (total_sum - own_value) / (total_count - 1)
        else:
            rates[getattr(row, id_col)] = 0.0
    return rates


def _build_cycle_features(
    cycles: pd.DataFrame, usage: pd.DataFrame, factory: pd.DataFrame, batch_rate: dict, station_rate: dict
) -> pd.DataFrame:
    usage_map = usage.set_index("cell_id")
    lot_map = factory.set_index("cell_id")["lot_id"].to_dict()
    station_map = factory.set_index("cell_id")["station_id"].to_dict()
    batch_map = factory.set_index("cell_id")["batch_id"].to_dict()

    out = []
    w, dw = config.ROLLING_WINDOW, config.SOH_DELTA_WINDOW
    for cell_id, g in cycles.groupby("cell_id", sort=False):
        g = g.sort_values("cycle_index").reset_index(drop=True)
        init_cap = _initial_capacity(g)
        init_res = float(g["internal_resistance_mohm"].head(5).mean())
        soh = (g["discharge_capacity_ah"] / init_cap).to_numpy()
        ci = g["cycle_index"].to_numpy()

        feat = pd.DataFrame({"cell_id": cell_id, "cycle_index": ci})
        feat["cycle_count"] = ci
        feat["soh_current"] = soh
        # Average fade/growth rate since beginning of life (per cycle).
        feat["capacity_fade_rate"] = (1.0 - soh) / np.maximum(ci, 1)
        feat["resistance_growth_rate"] = (g["internal_resistance_mohm"].to_numpy() / init_res - 1.0) / np.maximum(ci, 1)
        feat["rolling_capacity_mean_10"] = g["discharge_capacity_ah"].rolling(w, min_periods=1).mean().to_numpy()
        feat["rolling_temperature_max_10"] = g["temperature_max"].rolling(w, min_periods=1).max().to_numpy()
        feat["rolling_resistance_mean_10"] = g["internal_resistance_mohm"].rolling(w, min_periods=1).mean().to_numpy()
        feat["soh_delta_last_20_cycles"] = pd.Series(soh).diff(dw).fillna(0.0).to_numpy()

        # Per-cell usage + manufacturing context (broadcast to every cycle row).
        u = usage_map.loc[cell_id]
        feat["fast_charge_ratio"] = float(u["fast_charge_ratio"])
        feat["avg_depth_of_discharge"] = float(u["avg_depth_of_discharge"])
        feat["high_temp_exposure_hours"] = float(u["high_temp_exposure_hours"])
        feat["batch_failure_rate"] = batch_rate.get(cell_id, 0.0)
        feat["station_anomaly_rate"] = station_rate.get(cell_id, 0.0)
        feat["lot_id"] = lot_map[cell_id]
        feat["station_id"] = station_map[cell_id]

        # Regression targets.
        feat["remaining_cycles"] = _remaining_cycles(soh, ci)
        out.append(feat)

    result = pd.concat(out, ignore_index=True)
    return result


def _build_cell_features(
    cycle_features: pd.DataFrame, usage: pd.DataFrame, factory: pd.DataFrame, failures: pd.DataFrame,
    batch_rate: dict, station_rate: dict,
) -> pd.DataFrame:
    """Aggregate to one row per cell for the failure-risk classifier."""
    last = cycle_features.sort_values("cycle_index").groupby("cell_id").tail(1).set_index("cell_id")
    agg = cycle_features.groupby("cell_id").agg(
        cycle_count=("cycle_index", "max"),
        capacity_fade_rate=("capacity_fade_rate", "last"),
        resistance_growth_rate=("resistance_growth_rate", "last"),
        final_soh=("soh_current", "last"),
    )
    factory_idx = factory.set_index("cell_id")
    usage_idx = usage.set_index("cell_id")

    # Temperature exposure summarised from the raw cycle table.
    cyc = pd.read_csv(config.CYCLES_CSV)
    temp = cyc.groupby("cell_id").agg(
        peak_temperature_max=("temperature_max", "max"),
        mean_temperature_max=("temperature_max", "mean"),
    )

    df = agg.join(temp)
    df["fast_charge_ratio"] = usage_idx["fast_charge_ratio"]
    df["avg_depth_of_discharge"] = usage_idx["avg_depth_of_discharge"]
    df["high_temp_exposure_hours"] = usage_idx["high_temp_exposure_hours"]
    df["low_temp_exposure_hours"] = usage_idx["low_temp_exposure_hours"]
    df["usage_profile"] = usage_idx["usage_profile"]
    df["lot_id"] = factory_idx["lot_id"]
    df["station_id"] = factory_idx["station_id"]
    df["batch_id"] = factory_idx["batch_id"]
    cell_index = df.index.to_series()
    df["batch_failure_rate"] = cell_index.map(batch_rate).fillna(0.0).to_numpy()
    df["station_anomaly_rate"] = cell_index.map(station_rate).fillna(0.0).to_numpy()

    # Classification target.
    fail_idx = failures.set_index("cell_id")
    df["escalation_required"] = fail_idx["escalation_required"].astype(int)
    df["failure_severity"] = fail_idx["failure_severity"]
    return df.reset_index()


def build() -> dict[str, pd.DataFrame]:
    """Build and persist both feature tables; return them as a dict."""
    config.ensure_dirs()
    factory, cycles, usage, failures = _read_processed()

    # Group-level rates computed once and reused as features. Each cell receives
    # peer-only rates so its own target/event row cannot leak back into features.
    merged = failures.merge(factory[["cell_id", "batch_id", "station_id"]], on="cell_id")
    batch_rate = _leave_one_out_group_rate(merged, "batch_id", "escalation_required")
    station_rate = _leave_one_out_group_rate(merged, "station_id", "thermal_anomaly_event")

    cycle_features = _build_cycle_features(cycles, usage, factory, batch_rate, station_rate)
    cell_features = _build_cell_features(cycle_features, usage, factory, failures, batch_rate, station_rate)

    cycle_features.to_csv(config.CYCLE_FEATURES_CSV, index=False)
    cell_features.to_csv(config.CELL_FEATURES_CSV, index=False)

    log_dataframe(log, "cycle_features", cycle_features)
    log_dataframe(log, "cell_features", cell_features)
    log.info("Class balance (escalation_required): %s", cell_features["escalation_required"].value_counts().to_dict())
    return {"cycle_features": cycle_features, "cell_features": cell_features}


if __name__ == "__main__":
    build()
