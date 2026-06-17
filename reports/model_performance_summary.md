# Model Performance Summary

_Generated: 2026-06-17 • all data synthetic; no Apple confidential data used._

## 1. State of Health (SOH) regression
- **Algorithm:** GradientBoosting
- **Target:** `soh_current` = discharge_capacity / initial_capacity
- **Validation:** cell-grouped hold-out (25% of cells)

| Metric | Value |
| --- | --- |
| MAE  | 0.0107 |
| RMSE | 0.0160 |
| R²   | 0.948 |

Top drivers (permutation_importance):

| Feature | Importance |
| --- | --- |
| `rolling_resistance_mean_10` | 0.6537 |
| `cycle_count` | 0.2731 |
| `resistance_growth_rate` | 0.0794 |
| `fast_charge_ratio` | 0.0313 |
| `high_temp_exposure_hours` | 0.0058 |
| `rolling_temperature_max_10` | 0.0038 |

## 2. Remaining Useful Life (RUL) regression
- **Algorithm:** GradientBoosting
- **Target:** `remaining_cycles` until SOH < 80%
- **Validation:** cell-grouped hold-out

| Metric | Value |
| --- | --- |
| MAE  | 46.1 cycles |
| RMSE | 70.1 cycles |
| R²   | 0.926 |

Top drivers (permutation_importance):

| Feature | Importance |
| --- | --- |
| `soh_current` | 0.7839 |
| `capacity_fade_rate` | 0.0941 |
| `resistance_growth_rate` | 0.0921 |
| `fast_charge_ratio` | 0.0643 |
| `station_anomaly_rate` | 0.0043 |
| `batch_failure_rate` | 0.0043 |

## 3. Failure-risk classification
- **Algorithm:** LogisticRegression
- **Target:** `escalation_required` (engineering escalation needed)
- **Validation:** stratified cell-level hold-out

| Metric | Value |
| --- | --- |
| Precision | 0.750 |
| Recall    | 1.000 |
| F1        | 0.857 |
| ROC-AUC   | 0.993 |

Confusion matrix (rows = actual, cols = predicted):

|            | Pred 0 | Pred 1 |
| ---------- | ------ | ------ |
| **Actual 0** | 22 | 2 |
| **Actual 1** | 0 | 6 |

Top drivers (permutation_importance):

| Feature | Importance |
| --- | --- |
| `capacity_fade_rate` | 0.1367 |
| `final_soh` | 0.0700 |
| `station_anomaly_rate` | 0.0700 |
| `mean_temperature_max` | 0.0400 |
| `peak_temperature_max` | 0.0167 |
| `resistance_growth_rate` | 0.0133 |

## 4. Leading drivers of high-risk degradation
Across the failure classifier, the dominant degradation drivers are the
engineered fade/resistance/thermal features — consistent with the physics of
lithium-ion ageing (capacity fade + impedance growth accelerated by thermal and
fast-charge stress). These same drivers populate the `top_risk_driver` column of
the escalation queue so each flagged cell carries a likely root cause.
