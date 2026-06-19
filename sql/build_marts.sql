-- ===========================================================================
-- Analytics marts (consumed by reporting + Tableau extracts).
-- Rebuildable at any time via CREATE TABLE AS SELECT. Safe to run repeatedly.
-- ===========================================================================

-- ----- mart_cell_health_summary --------------------------------------------
-- One row per cell: manufacturing context + latest health + model scores.
DROP TABLE IF EXISTS mart_cell_health_summary;
CREATE TABLE mart_cell_health_summary AS
SELECT
    c.cell_id,
    c.lot_id,
    c.batch_id,
    c.station_id,
    c.usage_profile,
    f.cycle_count,
    ROUND(f.final_soh, 4)               AS last_soh,
    ROUND(f.capacity_fade_rate, 6)      AS capacity_fade_rate,
    ROUND(f.resistance_growth_rate, 6)  AS resistance_growth_rate,
    ROUND(f.peak_temperature_max, 2)    AS peak_temperature_max,
    p.predicted_soh,
    p.predicted_remaining_cycles,
    p.failure_probability,
    p.risk_tier,
    p.early_warning_probability,
    p.early_warning_risk_tier,
    p.top_risk_driver,
    fe.escalation_required,
    fe.failure_severity
FROM dim_cell c
JOIN stg_cell_features f       ON f.cell_id = c.cell_id
LEFT JOIN fact_model_predictions p ON p.cell_id = c.cell_id
LEFT JOIN fact_failure_events fe   ON fe.cell_id = c.cell_id;

-- ----- mart_factory_quality ------------------------------------------------
-- Lot x station quality rollup for the factory-quality dashboard page.
DROP TABLE IF EXISTS mart_factory_quality;
CREATE TABLE mart_factory_quality AS
SELECT
    c.lot_id,
    c.station_id,
    COUNT(*)                                              AS num_cells,
    ROUND(AVG(f.final_soh), 4)                            AS avg_final_soh,
    ROUND(AVG(f.capacity_fade_rate), 6)                   AS avg_capacity_fade_rate,
    ROUND(AVG(f.resistance_growth_rate), 6)               AS avg_resistance_growth_rate,
    ROUND(AVG(fe.escalation_required), 4)                 AS escalation_rate,
    ROUND(AVG(fe.early_degradation_flag), 4)              AS early_degradation_rate,
    ROUND(AVG(fe.thermal_anomaly_event), 4)               AS thermal_anomaly_rate,
    ROUND(AVG(fe.impedance_spike_event), 4)               AS impedance_spike_rate
FROM dim_cell c
JOIN stg_cell_features f     ON f.cell_id = c.cell_id
JOIN fact_failure_events fe  ON fe.cell_id = c.cell_id
GROUP BY c.lot_id, c.station_id;

-- ----- mart_escalation_queue -----------------------------------------------
-- Cells needing engineering attention today: model says High/Critical risk OR
-- the failure-event record already flagged an escalation.
DROP TABLE IF EXISTS mart_escalation_queue;
CREATE TABLE mart_escalation_queue AS
SELECT
    s.cell_id,
    s.lot_id,
    s.station_id,
    s.usage_profile,
    s.failure_probability,
    s.early_warning_probability,
    s.early_warning_risk_tier,
    s.predicted_soh,
    s.predicted_remaining_cycles,
    s.last_soh,
    s.capacity_fade_rate,
    s.resistance_growth_rate,
    s.peak_temperature_max,
    s.risk_tier,
    s.top_risk_driver,
    s.failure_severity
FROM mart_cell_health_summary s
WHERE s.risk_tier IN ('High', 'Critical')
   OR s.escalation_required = 1
ORDER BY s.failure_probability DESC, s.predicted_remaining_cycles ASC;
