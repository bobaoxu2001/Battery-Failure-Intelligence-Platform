# AI Skill — Natural-Language → SQL Report Generation

> Reusable LLM skill. Turns a plain-English engineering question into a correct
> SQL query against the Battery Failure Intelligence warehouse, runs it, and
> returns a short written answer plus the table.

## When to use
An engineer or manager asks a data question in words — *"which lots are
degrading fastest this week?"* — and wants an answer without writing SQL.

## Warehouse schema the skill must reason over
Dimensions: `dim_cell`, `dim_lot`, `dim_station`, `dim_test_condition`
Facts: `fact_cycle_measurements`, `fact_usage_profile`, `fact_failure_events`,
`fact_model_predictions`
Marts (prefer these for reporting):
- `mart_cell_health_summary` — one row/cell: SOH, fade, predictions, risk tier
- `mart_factory_quality` — lot × station rollup: escalation/anomaly rates
- `mart_escalation_queue` — cells needing attention, with `top_risk_driver`

Full DDL is in `sql/create_schema.sql`; canonical examples in
`sql/example_ad_hoc_queries.sql`.

## Procedure
1. **Identify grain & metric**: per-cell, per-lot, per-station, or fleet-level?
   What is being measured (SOH, fade rate, escalation rate, count)?
2. **Pick the smallest table that answers it** — prefer a mart over raw facts.
3. **Generate SQLite-compatible SQL**. Rules:
   - `ROUND(x, n)` for readability; alias every computed column.
   - Use `AVG(escalation_required)` for rates (the flag is 0/1).
   - Always `ORDER BY` the metric of interest and `LIMIT` long results.
   - No vendor-specific syntax (must run on SQLite **and** DuckDB).
4. **Dry-run mentally**: do all referenced columns exist? Is the join key right?
5. **Run, then summarise**: 1–2 sentences of plain-English insight + the table.

## Few-shot mapping
| Question | Target table | Key clause |
| --- | --- | --- |
| "Highest-risk lots?" | `mart_factory_quality` | `GROUP BY lot_id ORDER BY escalation_rate DESC` |
| "Which stations look abnormal?" | `mart_factory_quality` | `ORDER BY thermal_anomaly_rate DESC` |
| "What needs escalation today?" | `mart_escalation_queue` | `ORDER BY failure_probability DESC` |
| "Drivers by usage profile?" | `mart_cell_health_summary` | `GROUP BY usage_profile` |
| "Temp exposure vs fade?" | `stg_cell_features` | bucket `high_temp_exposure_hours` |

## Output format
```
Question:  <restated>
SQL:       <final query>
Answer:    <1–2 sentence insight>
Table:     <top N rows>
```

## Guardrails
- Read-only: only `SELECT`. Never `INSERT/UPDATE/DELETE/DROP`.
- If a column/table is not in the schema above, say so instead of inventing it.
- If the question is ambiguous on grain or time window, state the assumption used.
