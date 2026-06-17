"""Ingest the synthetic landing-zone files into a clean ``processed`` layer.

In a real engineering data platform this step would read vendor cycler exports,
MES factory dumps and field telemetry. Here it reads the synthetic landing zone
(``data/synthetic``), applies light validation/cleaning, enforces dtypes, and
writes the canonical processed tables the warehouse and feature code consume.

Run as a module::

    python -m src.ingest.load_raw_data
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.ingest.generate_synthetic_battery_data import generate
from src.utils.logging_utils import get_logger, log_dataframe

log = get_logger(__name__)

# Required columns per table; used to fail fast on malformed source files.
REQUIRED_COLUMNS = {
    "factory": ["cell_id", "lot_id", "batch_id", "station_id", "manufacturing_date"],
    "cycles": ["cell_id", "cycle_index", "discharge_capacity_ah", "internal_resistance_mohm"],
    "usage": ["cell_id", "usage_profile", "fast_charge_ratio"],
    "failure_events": ["cell_id", "escalation_required", "failure_severity"],
}


def _read_or_generate() -> dict[str, pd.DataFrame]:
    """Load synthetic source files, generating them first if they are missing."""
    expected = {name: config.SYNTHETIC_DIR / f"{name}.csv" for name in REQUIRED_COLUMNS}
    if not all(path.exists() for path in expected.values()):
        log.info("Synthetic source files missing -> generating them now")
        return generate()
    return {name: pd.read_csv(path) for name, path in expected.items()}


def _validate(name: str, frame: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in frame.columns]
    if missing:
        raise ValueError(f"Source table '{name}' is missing required columns: {missing}")
    if frame.empty:
        raise ValueError(f"Source table '{name}' is empty")


def _clean_cycles(cycles: pd.DataFrame) -> pd.DataFrame:
    """Drop physically-impossible rows and de-duplicate cell/cycle keys."""
    before = len(cycles)
    cycles = cycles.dropna(subset=["discharge_capacity_ah", "internal_resistance_mohm"])
    cycles = cycles[cycles["discharge_capacity_ah"] > 0]
    cycles = cycles[cycles["internal_resistance_mohm"] > 0]
    cycles = cycles.drop_duplicates(subset=["cell_id", "cycle_index"])
    cycles = cycles.sort_values(["cell_id", "cycle_index"]).reset_index(drop=True)
    removed = before - len(cycles)
    if removed:
        log.info("Cleaned cycles: removed %d invalid/duplicate rows", removed)
    return cycles


def load() -> dict[str, pd.DataFrame]:
    """Validate, clean and persist the processed tables; return them as a dict."""
    config.ensure_dirs()
    raw = _read_or_generate()

    for name, frame in raw.items():
        _validate(name, frame)

    factory = raw["factory"].copy()
    cycles = _clean_cycles(raw["cycles"].copy())
    usage = raw["usage"].copy()
    failures = raw["failure_events"].copy()

    factory.to_csv(config.FACTORY_CSV, index=False)
    cycles.to_csv(config.CYCLES_CSV, index=False)
    usage.to_csv(config.USAGE_CSV, index=False)
    failures.to_csv(config.FAILURES_CSV, index=False)

    for name, frame in {"factory": factory, "cycles": cycles, "usage": usage, "failures": failures}.items():
        log_dataframe(log, f"processed/{name}", frame)

    log.info("Processed layer written to %s", config.PROCESSED_DIR)
    return {"factory": factory, "cycles": cycles, "usage": usage, "failure_events": failures}


if __name__ == "__main__":
    load()
