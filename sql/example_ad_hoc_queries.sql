-- ===========================================================================
-- Example ad-hoc engineering / business questions against the warehouse.
-- These mirror the kind of questions a battery-reliability team asks daily and
-- double as a reference for the AI SQL-generation skill (ai_workflows/).
-- ===========================================================================

-- Q1. Which lots have the highest early-degradation / escalation risk?
SELECT
    lot_id,
    SUM(num_cells)                                   AS cells,
    ROUND(SUM(escalation_rate * num_cells) / SUM(num_cells), 4)        AS escalation_rate,
    ROUND(SUM(early_degradation_rate * num_cells) / SUM(num_cells), 4) AS early_degradation_rate,
    ROUND(SUM(avg_final_soh * num_cells) / SUM(num_cells), 4)          AS avg_final_soh
FROM mart_factory_quality
GROUP BY lot_id
ORDER BY escalation_rate DESC, early_degradation_rate DESC
LIMIT 10;

-- Q2. Which test stations have abnormal failure / anomaly rates?
SELECT
    station_id,
    SUM(num_cells)                                              AS cells,
    ROUND(SUM(thermal_anomaly_rate * num_cells) / SUM(num_cells), 4)  AS thermal_anomaly_rate,
    ROUND(SUM(impedance_spike_rate * num_cells) / SUM(num_cells), 4)  AS impedance_spike_rate,
    ROUND(SUM(escalation_rate * num_cells) / SUM(num_cells), 4)       AS escalation_rate
FROM mart_factory_quality
GROUP BY station_id
HAVING escalation_rate > (
    SELECT AVG(escalation_required) FROM fact_failure_events
)
ORDER BY thermal_anomaly_rate DESC;

-- Q3. Which cells require urgent escalation today (top of the queue)?
SELECT
    cell_id, lot_id, station_id, risk_tier,
    ROUND(failure_probability, 3) AS failure_probability,
    predicted_soh, predicted_remaining_cycles, top_risk_driver
FROM mart_escalation_queue
ORDER BY failure_probability DESC, predicted_remaining_cycles ASC
LIMIT 20;

-- Q4. What are the top degradation drivers by usage profile?
SELECT
    s.usage_profile,
    COUNT(*)                                  AS cells,
    ROUND(AVG(s.capacity_fade_rate), 6)       AS avg_capacity_fade_rate,
    ROUND(AVG(s.resistance_growth_rate), 6)   AS avg_resistance_growth_rate,
    ROUND(AVG(s.last_soh), 4)                 AS avg_last_soh,
    ROUND(AVG(s.failure_probability), 4)      AS avg_failure_probability
FROM mart_cell_health_summary s
GROUP BY s.usage_profile
ORDER BY avg_failure_probability DESC;

-- Q5. How does thermal exposure correlate with capacity fade?
-- Bucketed view of high-temperature exposure vs. average fade rate / SOH.
SELECT
    CASE
        WHEN f.high_temp_exposure_hours < 40  THEN '0-40h'
        WHEN f.high_temp_exposure_hours < 80  THEN '40-80h'
        WHEN f.high_temp_exposure_hours < 120 THEN '80-120h'
        ELSE '120h+'
    END                                       AS high_temp_exposure_band,
    COUNT(*)                                  AS cells,
    ROUND(AVG(f.capacity_fade_rate), 6)       AS avg_capacity_fade_rate,
    ROUND(AVG(f.final_soh), 4)                AS avg_final_soh,
    ROUND(AVG(fe.thermal_anomaly_event), 4)   AS thermal_anomaly_rate
FROM stg_cell_features f
JOIN fact_failure_events fe ON fe.cell_id = f.cell_id
GROUP BY high_temp_exposure_band
ORDER BY avg_capacity_fade_rate DESC;

-- Q6. Fleet health snapshot by risk tier.
SELECT
    COALESCE(risk_tier, 'Unscored') AS risk_tier,
    COUNT(*)                        AS cells,
    ROUND(AVG(predicted_soh), 4)    AS avg_predicted_soh,
    ROUND(AVG(predicted_remaining_cycles), 1) AS avg_remaining_cycles
FROM mart_cell_health_summary
GROUP BY risk_tier
ORDER BY cells DESC;
