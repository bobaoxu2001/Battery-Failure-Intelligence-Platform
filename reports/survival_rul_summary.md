# Censored RUL Survival Model

_Generated: 2026-06-20._

This model estimates time-to-80% SOH with right-censoring. Cells that never cross the EOL threshold are treated as observed-safe until their final recorded cycle, not as permanent non-failures.

## Model Design

- Interval width: 50 cycles
- Estimator: logistic discrete-time hazard model
- Features: `fast_charge_ratio`, `avg_depth_of_discharge`, `high_temp_exposure_hours`, `low_temp_exposure_hours`, `station_anomaly_rate`, `usage_profile`, `log_interval_end`
- Training cells: 84
- Holdout cells: 36
- Manufacturing-date cutoff: 2024-05-20

## Holdout Metrics

| Metric | Value |
| --- | --- |
| Train event rate | 0.262 |
| Holdout event rate | 0.333 |
| Event-cycle MAE | 110.4 cycles |
| Median-event baseline MAE | 63.5 cycles |
| Concordance index | 0.757 |

## Sample Holdout Predictions

| Cell | Event observed | Observed duration | Pred expected EOL | Pred remaining from observed | Event probability by 500 cycles |
| --- | --- | --- | --- | --- | --- |
| CELL-00095 | 0 | 276 | 253.8 | 0.0 | 1.000 |
| CELL-00034 | 0 | 468 | 278.2 | 0.0 | 1.000 |
| CELL-00037 | 1 | 313 | 297.8 | 0.0 | 1.000 |
| CELL-00013 | 0 | 251 | 297.9 | 46.9 | 1.000 |
| CELL-00101 | 1 | 557 | 300.5 | 0.0 | 1.000 |
| CELL-00019 | 1 | 432 | 303.1 | 0.0 | 1.000 |
| CELL-00033 | 1 | 510 | 303.4 | 0.0 | 1.000 |
| CELL-00031 | 0 | 295 | 305.2 | 10.2 | 1.000 |
| CELL-00070 | 1 | 463 | 317.3 | 0.0 | 1.000 |
| CELL-00117 | 1 | 482 | 338.7 | 0.0 | 1.000 |

## Why this matters

A standard RUL regressor needs a numeric remaining-life target for every row. Real battery programs often have cells that have not failed yet, so the target is censored. This module shows the release path for that more realistic setting without pretending censored cells have known final lifetimes.
