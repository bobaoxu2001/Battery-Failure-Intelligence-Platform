# Model Monitoring Summary

_Generated: 2026-06-20 - synthetic cohort monitoring._

7 monitored feature(s) are in watch/alert status.

## Feature Stability

| feature | reference_mean | current_mean | delta | psi | status |
| --- | --- | --- | --- | --- | --- |
| peak_temperature_max | 45.7953 | 46.0340 | 0.2387 | 1.2850 | alert |
| final_soh | 0.8354 | 0.8452 | 0.0098 | 1.2410 | alert |
| resistance_growth_rate | 0.0025 | 0.0023 | -0.0002 | 0.4719 | alert |
| fast_charge_ratio | 0.2731 | 0.2888 | 0.0157 | 0.3155 | alert |
| capacity_fade_rate | 0.0004 | 0.0003 | -0.0000 | 0.2907 | alert |

## Current Cohort Risk Mix

| risk_tier | current_cells |
| --- | --- |
| Critical | 7 |
| High | 1 |
| Low | 26 |
| Medium | 2 |

## Current Cohort Leading Drivers

| top_risk_driver | current_cells |
| --- | --- |
| Accelerated capacity fade | 10 |
| Test-station anomaly signal | 9 |
| Deep discharge cycling | 7 |
| Low state of health | 5 |
| Sustained thermal exposure | 3 |
| High-temperature field exposure | 1 |
| High cumulative cycle count | 1 |

## Operating Guidance
1. Treat `alert` PSI features as candidates for root-cause review by lot/station.
2. If risk mix shifts toward High/Critical, inspect the escalation queue before retraining.
3. Re-run after each daily pipeline refresh and compare the generated CSV over time.
