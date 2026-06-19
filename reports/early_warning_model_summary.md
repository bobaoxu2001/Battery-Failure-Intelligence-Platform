# Early-Warning Failure Model

_Generated: 2026-06-20._

This model predicts eventual escalation from the first 50 cycles plus factory/test condition context. It is separate from the retrospective investigation model so lifetime-only fields cannot leak into early-warning decisions.

## Feature Boundary

- Allowed: first-50-cycle SOH/resistance/temperature/voltage summaries, acceptance-test settings, station peer context.
- Excluded: `final_soh`, full-life `cycle_count`, lifetime peak temperature, full-life fade rate, failure labels, and post-outcome fields.

## Holdout Metrics

- Algorithm: RandomForest

| Metric | Value |
| --- | --- |
| Precision | 1.000 |
| Recall | 0.667 |
| F1 | 0.800 |
| ROC-AUC | 1.000 |

Confusion matrix (rows = actual, cols = predicted):

|            | Pred 0 | Pred 1 |
| ---------- | ------ | ------ |
| **Actual 0** | 24 | 0 |
| **Actual 1** | 2 | 4 |

## Top First-Window Drivers

| Feature | Importance |
| --- | --- |
| `soh_at_cycle_50` | 0.0500 |
| `capacity_fade_rate_50` | 0.0400 |
| `temperature_mean_50` | 0.0100 |
| `early_cycle_count` | 0.0000 |
| `resistance_mean_50` | 0.0000 |
| `temperature_max_50` | 0.0000 |
| `voltage_min_50` | 0.0000 |
| `charge_current` | 0.0000 |

## Interpretation

Use this model for triage while cells are still early in life. Use the retrospective model for post-failure investigation, pass/fail comparison, and engineering root-cause analysis.
