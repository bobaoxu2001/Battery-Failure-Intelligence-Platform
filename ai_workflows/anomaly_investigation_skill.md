# AI Skill — Battery Cell Anomaly Investigation

> Reusable LLM skill. Given a single `cell_id`, the assistant inspects the
> cell's health, compares it to its batch/lot peers, identifies the most likely
> root cause, and recommends the next engineering step. Designed to plug into a
> Claude/agent workflow over the local warehouse.

## When to use
A reliability engineer asks *"what's going on with CELL-00032?"* or the daily
escalation report flags a cell and you need a fast, structured triage.

## Inputs
- `cell_id` (required)
- Read access to `data/processed/battery_warehouse.db` (SQLite)

## Context the skill should pull
Run these against the warehouse (see `sql/example_ad_hoc_queries.sql` for style):

```sql
-- 1. The cell's own health + model scores
SELECT * FROM mart_cell_health_summary WHERE cell_id = :cell_id;

-- 2. Batch / lot / station peer averages for comparison
SELECT 'batch' AS scope, AVG(last_soh) avg_soh, AVG(capacity_fade_rate) avg_fade,
       AVG(resistance_growth_rate) avg_res, AVG(failure_probability) avg_fp
FROM mart_cell_health_summary
WHERE batch_id = (SELECT batch_id FROM mart_cell_health_summary WHERE cell_id = :cell_id);

-- 3. The cell's degradation trajectory (last 50 cycles)
SELECT cycle_index, discharge_capacity_ah, internal_resistance_mohm, temperature_max
FROM fact_cycle_measurements WHERE cell_id = :cell_id
ORDER BY cycle_index DESC LIMIT 50;

-- 4. Any logged failure events
SELECT * FROM fact_failure_events WHERE cell_id = :cell_id;
```

## Reasoning steps (the skill's "chain")
1. **Summarise the cell**: SOH, fade rate, resistance growth, peak temperature,
   risk tier, predicted remaining cycles.
2. **Compare to peers**: is each metric within ~1σ of its batch/lot mean, or an
   outlier? Quantify the deviation (e.g. "fade rate 2.3× batch median").
3. **Classify the signature** using these heuristics:
   - High resistance growth + impedance spike → **internal resistance / impedance fault**
   - Steep capacity fade + normal resistance → **active-material / lithium-inventory loss**
   - High `temperature_max` + thermal_anomaly_event → **thermal management issue**
   - Whole batch/lot deviates together → **systemic factory/process issue (not a one-off)**
   - Only this cell deviates, peers normal → **isolated defect**
4. **Cross-check the test station**: if the cell's station has a high
   `thermal_anomaly_rate` in `mart_factory_quality`, consider **measurement /
   calibration artifact** before condemning the cell.
5. **Recommend the next step** (teardown, EIS impedance sweep, reference
   performance test, hold the lot, re-test on a reference station, etc.).

## Output format
```
Cell: <cell_id>  |  Risk tier: <tier>  |  Fail prob: <p>
Health:   SOH <x> (batch avg <y>), fade <x> (<n>× batch), Rgrowth <x>
Verdict:  <one-line root-cause hypothesis>
Evidence: <2–3 bullet metrics vs peers>
Action:   <single recommended engineering follow-up>
Confidence: <low|medium|high> + what would raise it
```

## Guardrails
- Never claim certainty from one cell; state confidence and what evidence is missing.
- Distinguish **cell defect** vs **station/measurement artifact** before recommending scrap.
- All data is synthetic; do not reference Apple-internal systems or real part numbers.
