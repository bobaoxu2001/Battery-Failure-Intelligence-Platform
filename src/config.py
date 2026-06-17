"""Central configuration for the Battery Failure Intelligence Platform.

All paths, modeling thresholds, and synthetic-data parameters live here so the
rest of the codebase reads from a single source of truth. Values can be tuned
for a fast smoke test by exporting ``BFI_QUICK=1`` (used by CI).
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# ROOT is the repository root (one level above ``src/``).
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROCESSED_DIR / "models"

SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"
DASHBOARDS_DIR = ROOT / "dashboards"
TABLEAU_EXTRACTS_DIR = DASHBOARDS_DIR / "tableau_extracts"
MOCKUPS_DIR = DASHBOARDS_DIR / "screenshots_or_mockups"

# Local analytics warehouse (SQLite keeps the project dependency-free; DuckDB
# can be swapped in by pointing ``WAREHOUSE_DB`` at a ``.duckdb`` file).
WAREHOUSE_DB = PROCESSED_DIR / "battery_warehouse.db"

# Canonical processed table file names.
FACTORY_CSV = PROCESSED_DIR / "factory.csv"
CYCLES_CSV = PROCESSED_DIR / "cycles.csv"
USAGE_CSV = PROCESSED_DIR / "usage.csv"
FAILURES_CSV = PROCESSED_DIR / "failure_events.csv"
CYCLE_FEATURES_CSV = PROCESSED_DIR / "cycle_features.csv"
CELL_FEATURES_CSV = PROCESSED_DIR / "cell_features.csv"
PREDICTIONS_CSV = PROCESSED_DIR / "model_predictions.csv"

# Raw telemetry log used to demonstrate the Unix/Perl ingest path.
RAW_LOG_FILE = RAW_DIR / "raw_battery_test_logs.txt"
PARSED_LOG_CSV = PROCESSED_DIR / "parsed_raw_logs.csv"

# --------------------------------------------------------------------------- #
# Reproducibility / scale
# --------------------------------------------------------------------------- #
SEED = 42
QUICK_MODE = os.getenv("BFI_QUICK", "0") == "1"

# Number of simulated cells and per-cell cycle-life bounds. Quick mode reduces
# the *cell count* (for a fast CI run) but keeps the full cycle-life range so the
# degradation/escalation signal — and both classes for the classifier — survive.
N_CELLS = 45 if QUICK_MODE else 120
MIN_LIFE_CYCLES = 250
MAX_LIFE_CYCLES = 650

# Manufacturing topology.
N_LOTS = 6 if QUICK_MODE else 12
N_STATIONS = 4 if QUICK_MODE else 8
N_EQUIPMENT = 3 if QUICK_MODE else 6

# Nominal cell electrical characteristics.
NOMINAL_CAPACITY_AH = 3.50
NOMINAL_VOLTAGE_V = 3.70
NOMINAL_RESISTANCE_MOHM = 25.0

# --------------------------------------------------------------------------- #
# Modeling / business thresholds
# --------------------------------------------------------------------------- #
# State of health (SOH) end-of-life threshold; below this a cell is "spent".
SOH_EOL_THRESHOLD = 0.80
# A cell degrading materially faster than the fleet is flagged "early".
EARLY_DEGRADATION_SOH = 0.90

# Rolling-window size (in cycles) for engineered trend features.
ROLLING_WINDOW = 10
SOH_DELTA_WINDOW = 20

# Failure-probability cut points used to assign a discrete risk tier.
RISK_TIER_THRESHOLDS = {
    "Critical": 0.80,
    "High": 0.55,
    "Medium": 0.30,
    # anything below "Medium" is "Low"
}

# Test split fraction (cells are split, not rows, to avoid leakage).
TEST_SIZE = 0.25

# Columns that every escalation row must carry (used by tests + reports).
ESCALATION_COLUMNS = [
    "cell_id",
    "lot_id",
    "station_id",
    "failure_probability",
    "predicted_soh",
    "predicted_remaining_cycles",
    "likely_root_cause",
    "recommended_follow_up",
]


def ensure_dirs() -> None:
    """Create every directory the pipeline writes to (idempotent)."""
    for path in (
        RAW_DIR,
        SYNTHETIC_DIR,
        PROCESSED_DIR,
        MODELS_DIR,
        REPORTS_DIR,
        TABLEAU_EXTRACTS_DIR,
        MOCKUPS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
