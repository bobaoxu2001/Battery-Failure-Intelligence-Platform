-- ===========================================================================
-- Battery Failure Intelligence Platform - analytics warehouse schema
-- Engine: SQLite (DuckDB-compatible DDL). Star schema: conformed dimensions +
-- fact tables for cycle measurements, usage, failure events and model scores.
-- All data is synthetic; no Apple confidential data is used.
-- ===========================================================================

-- ----- Dimensions ----------------------------------------------------------
DROP TABLE IF EXISTS dim_cell;
CREATE TABLE dim_cell (
    cell_id            TEXT PRIMARY KEY,
    lot_id             TEXT NOT NULL,
    batch_id           TEXT NOT NULL,
    station_id         TEXT NOT NULL,
    equipment_id       TEXT,
    test_condition_id  INTEGER,
    usage_profile      TEXT,
    manufacturing_date TEXT,
    test_date          TEXT
);

DROP TABLE IF EXISTS dim_lot;
CREATE TABLE dim_lot (
    lot_id      TEXT PRIMARY KEY,
    num_cells   INTEGER,
    num_batches INTEGER
);

DROP TABLE IF EXISTS dim_station;
CREATE TABLE dim_station (
    station_id TEXT PRIMARY KEY,
    num_cells  INTEGER
);

DROP TABLE IF EXISTS dim_test_condition;
CREATE TABLE dim_test_condition (
    test_condition_id INTEGER PRIMARY KEY,
    test_temperature  REAL,
    charge_current    REAL,
    discharge_current REAL
);

-- ----- Facts ---------------------------------------------------------------
DROP TABLE IF EXISTS fact_cycle_measurements;
CREATE TABLE fact_cycle_measurements (
    cell_id                  TEXT NOT NULL,
    cycle_index              INTEGER NOT NULL,
    voltage_mean             REAL,
    voltage_min              REAL,
    voltage_max              REAL,
    current_mean             REAL,
    temperature_mean         REAL,
    temperature_max          REAL,
    discharge_capacity_ah    REAL,
    charge_capacity_ah       REAL,
    internal_resistance_mohm REAL,
    energy_wh                REAL,
    timestamp                TEXT,
    PRIMARY KEY (cell_id, cycle_index)
);

DROP TABLE IF EXISTS fact_usage_profile;
CREATE TABLE fact_usage_profile (
    cell_id                  TEXT PRIMARY KEY,
    avg_depth_of_discharge   REAL,
    fast_charge_ratio        REAL,
    avg_daily_cycles         REAL,
    high_temp_exposure_hours REAL,
    low_temp_exposure_hours  REAL,
    usage_profile            TEXT
);

DROP TABLE IF EXISTS fact_failure_events;
CREATE TABLE fact_failure_events (
    cell_id               TEXT PRIMARY KEY,
    event_date            TEXT,
    event_type            TEXT,
    capacity_drop_event   INTEGER,
    impedance_spike_event INTEGER,
    thermal_anomaly_event INTEGER,
    early_degradation_flag INTEGER,
    escalation_required   INTEGER,
    failure_severity      TEXT
);

DROP TABLE IF EXISTS fact_model_predictions;
CREATE TABLE fact_model_predictions (
    cell_id                   TEXT PRIMARY KEY,
    prediction_date           TEXT,
    predicted_soh             REAL,
    predicted_remaining_cycles REAL,
    failure_probability       REAL,
    risk_tier                 TEXT,
    top_risk_driver           TEXT
);

-- ----- Staging (engineered features used by the marts) ---------------------
-- These are loaded directly from the feature-engineering step. Keeping them in
-- the warehouse lets the marts and ad-hoc SQL reason over SOH/fade rates that
-- are expensive to recompute from raw cycle rows in pure SQL.
DROP TABLE IF EXISTS stg_cell_features;
CREATE TABLE stg_cell_features (
    cell_id                TEXT PRIMARY KEY,
    final_soh              REAL,
    capacity_fade_rate     REAL,
    resistance_growth_rate REAL,
    peak_temperature_max   REAL,
    mean_temperature_max   REAL,
    cycle_count            INTEGER,
    fast_charge_ratio      REAL,
    avg_depth_of_discharge REAL,
    high_temp_exposure_hours REAL,
    low_temp_exposure_hours  REAL,
    usage_profile          TEXT,
    lot_id                 TEXT,
    station_id             TEXT,
    batch_id               TEXT,
    batch_failure_rate     REAL,
    station_anomaly_rate   REAL,
    escalation_required    INTEGER,
    failure_severity       TEXT
);

CREATE INDEX IF NOT EXISTS idx_cycle_cell ON fact_cycle_measurements (cell_id);
CREATE INDEX IF NOT EXISTS idx_cell_lot   ON dim_cell (lot_id);
CREATE INDEX IF NOT EXISTS idx_cell_station ON dim_cell (station_id);
