-- ===========================================================================
-- Data-warehouse quality checks. Each query returns the COUNT of *offending*
-- rows for a named rule; the Python runner (warehouse/quality_checks.py) fails
-- the pipeline if any hard check is non-zero. Designed for SQLite/DuckDB.
-- ===========================================================================

-- name: orphan_cycle_cells (HARD)
-- Cycle measurements whose cell is missing from dim_cell.
SELECT COUNT(*) AS offending
FROM fact_cycle_measurements m
LEFT JOIN dim_cell c ON c.cell_id = m.cell_id
WHERE c.cell_id IS NULL;

-- name: null_discharge_capacity (HARD)
-- Cycle rows with missing or non-positive discharge capacity.
SELECT COUNT(*) AS offending
FROM fact_cycle_measurements
WHERE discharge_capacity_ah IS NULL OR discharge_capacity_ah <= 0;

-- name: negative_resistance (HARD)
-- Physically impossible internal resistance values.
SELECT COUNT(*) AS offending
FROM fact_cycle_measurements
WHERE internal_resistance_mohm <= 0;

-- name: duplicate_cell_cycle (HARD)
-- The (cell_id, cycle_index) grain must be unique.
SELECT COUNT(*) AS offending FROM (
    SELECT cell_id, cycle_index, COUNT(*) AS n
    FROM fact_cycle_measurements
    GROUP BY cell_id, cycle_index
    HAVING n > 1
);

-- name: usage_without_cell (HARD)
-- Usage rows that do not map to a known cell.
SELECT COUNT(*) AS offending
FROM fact_usage_profile u
LEFT JOIN dim_cell c ON c.cell_id = u.cell_id
WHERE c.cell_id IS NULL;

-- name: cell_missing_features (HARD)
-- Every known cell must have one staged feature row for marts/model reporting.
SELECT COUNT(*) AS offending
FROM dim_cell c
LEFT JOIN stg_cell_features f ON f.cell_id = c.cell_id
WHERE f.cell_id IS NULL;

-- name: feature_without_cell (HARD)
-- Staged feature rows must map back to the conformed cell dimension.
SELECT COUNT(*) AS offending
FROM stg_cell_features f
LEFT JOIN dim_cell c ON c.cell_id = f.cell_id
WHERE c.cell_id IS NULL;

-- name: prediction_without_cell (HARD)
-- Model predictions must map back to the conformed cell dimension.
SELECT COUNT(*) AS offending
FROM fact_model_predictions p
LEFT JOIN dim_cell c ON c.cell_id = p.cell_id
WHERE c.cell_id IS NULL;

-- name: soh_out_of_range (SOFT)
-- Engineered SOH should sit in a plausible band [0.4, 1.05].
SELECT COUNT(*) AS offending
FROM stg_cell_features
WHERE final_soh < 0.40 OR final_soh > 1.05;

-- name: escalation_missing_prediction (SOFT)
-- Cells flagged for escalation but never scored by the model.
SELECT COUNT(*) AS offending
FROM fact_failure_events fe
LEFT JOIN fact_model_predictions p ON p.cell_id = fe.cell_id
WHERE fe.escalation_required = 1 AND p.cell_id IS NULL;
