"""Build the local SQLite analytics warehouse from the processed tables.

Steps:
1. Execute ``sql/create_schema.sql`` to (re)create the star-schema tables.
2. Load conformed dimensions and fact tables from the processed CSVs.
3. Load engineered ``stg_cell_features`` (used by the marts).
4. Build the analytics marts via ``sql/build_marts.sql``.

The warehouse is a single SQLite file (``data/processed/battery_warehouse.db``)
so the whole project runs from a fresh clone with no database server. Swapping
to DuckDB only requires changing the connection in this module.

Run as a module::

    python -m src.warehouse.build_warehouse
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection to the warehouse file."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.WAREHOUSE_DB)


def execute_sql_file(conn: sqlite3.Connection, path) -> None:
    """Execute every statement in a ``.sql`` file."""
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def _build_dimensions(conn: sqlite3.Connection, factory: pd.DataFrame, usage: pd.DataFrame) -> None:
    # dim_test_condition: distinct charge/discharge current combinations.
    conds = (
        factory[["charge_current", "discharge_current"]]
        .drop_duplicates()
        .sort_values(["charge_current", "discharge_current"])
        .reset_index(drop=True)
    )
    conds["test_condition_id"] = conds.index + 1
    conds["test_temperature"] = config.NOMINAL_VOLTAGE_V * 0 + 25.0  # nominal setpoint
    cond_key = {(r.charge_current, r.discharge_current): r.test_condition_id for r in conds.itertuples()}

    # dim_cell
    usage_profile = usage.set_index("cell_id")["usage_profile"].to_dict()
    dim_cell = factory[["cell_id", "lot_id", "batch_id", "station_id", "equipment_id",
                        "manufacturing_date", "test_date", "charge_current", "discharge_current"]].copy()
    dim_cell["test_condition_id"] = dim_cell.apply(
        lambda r: cond_key[(r["charge_current"], r["discharge_current"])], axis=1
    )
    dim_cell["usage_profile"] = dim_cell["cell_id"].map(usage_profile)
    dim_cell = dim_cell[["cell_id", "lot_id", "batch_id", "station_id", "equipment_id",
                         "test_condition_id", "usage_profile", "manufacturing_date", "test_date"]]

    # dim_lot / dim_station
    dim_lot = factory.groupby("lot_id").agg(
        num_cells=("cell_id", "nunique"), num_batches=("batch_id", "nunique")
    ).reset_index()
    dim_station = factory.groupby("station_id").agg(num_cells=("cell_id", "nunique")).reset_index()
    dim_test_condition = conds[["test_condition_id", "test_temperature", "charge_current", "discharge_current"]]

    dim_cell.to_sql("dim_cell", conn, if_exists="append", index=False)
    dim_lot.to_sql("dim_lot", conn, if_exists="append", index=False)
    dim_station.to_sql("dim_station", conn, if_exists="append", index=False)
    dim_test_condition.to_sql("dim_test_condition", conn, if_exists="append", index=False)
    log.info("Loaded dims: cells=%d lots=%d stations=%d conditions=%d",
             len(dim_cell), len(dim_lot), len(dim_station), len(dim_test_condition))


def _build_facts(conn: sqlite3.Connection, cycles: pd.DataFrame, usage: pd.DataFrame,
                 failures: pd.DataFrame) -> None:
    cycles.to_sql("fact_cycle_measurements", conn, if_exists="append", index=False)
    usage.to_sql("fact_usage_profile", conn, if_exists="append", index=False)
    failures.to_sql("fact_failure_events", conn, if_exists="append", index=False)
    log.info("Loaded facts: cycle_measurements=%d usage=%d failure_events=%d",
             len(cycles), len(usage), len(failures))


def build_marts(conn: sqlite3.Connection) -> None:
    """(Re)build analytics marts. Safe to call after predictions are written."""
    execute_sql_file(conn, config.SQL_DIR / "build_marts.sql")
    log.info("Rebuilt analytics marts")


def build() -> None:
    """Full warehouse build from processed CSVs.

    Feature tables are required by the marts; if they are missing (e.g. the
    warehouse step runs before the feature step in the documented pipeline
    order) they are built on demand so this step is self-sufficient.
    """
    config.ensure_dirs()
    if not config.CELL_FEATURES_CSV.exists() or not config.CYCLE_FEATURES_CSV.exists():
        from src.features.build_features import build as build_features
        log.info("Feature tables missing - building them before the warehouse")
        build_features()

    factory = pd.read_csv(config.FACTORY_CSV)
    cycles = pd.read_csv(config.CYCLES_CSV)
    usage = pd.read_csv(config.USAGE_CSV)
    failures = pd.read_csv(config.FAILURES_CSV)
    cell_features = pd.read_csv(config.CELL_FEATURES_CSV)

    stg_cols = [
        "cell_id", "final_soh", "capacity_fade_rate", "resistance_growth_rate",
        "peak_temperature_max", "mean_temperature_max", "cycle_count",
        "fast_charge_ratio", "avg_depth_of_discharge", "high_temp_exposure_hours",
        "low_temp_exposure_hours", "usage_profile", "lot_id", "station_id",
        "batch_id", "batch_failure_rate", "station_anomaly_rate",
        "escalation_required", "failure_severity",
    ]

    with get_connection() as conn:
        execute_sql_file(conn, config.SQL_DIR / "create_schema.sql")
        _build_dimensions(conn, factory, usage)
        _build_facts(conn, cycles, usage, failures)
        cell_features[stg_cols].to_sql("stg_cell_features", conn, if_exists="append", index=False)
        build_marts(conn)
        conn.commit()
    log.info("Warehouse built at %s", config.WAREHOUSE_DB)


if __name__ == "__main__":
    build()
