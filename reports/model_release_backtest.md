# Model Release Backtest

_Generated: 2026-06-20._

This is a release-style validation pass, not a one-off train/test score. Models are trained on older manufacturing cohorts and evaluated on later cells to mimic a new-lot rollout.

## Release Split

- Training cells: 84
- Holdout cells: 36
- Holdout cycle rows: 16014
- Manufacturing-date cutoff: 2024-05-20

## Baseline Comparison

| Target | Model / baseline | Primary metric | Value |
| --- | --- | --- | --- |
| SOH | RandomForest | RMSE | 0.0150 |
| SOH | fleet_median_fade_baseline | RMSE | 0.0272 |
| RUL | GradientBoosting | MAE cycles | 48.1 |
| RUL | current_fade_to_eol_baseline | MAE cycles | 57.0 |
| Failure risk | LogisticRegression | F1 | 0.857 |
| Failure risk | soh_station_rule_baseline | F1 | 0.400 |

## Escalation Threshold Review

False negatives are weighted 5x false positives to reflect the cost of missing a risky cell. The chosen threshold is the lowest-cost point on the holdout cohort.

| Threshold | TP | FP | TN | FN | Precision | Recall | Review load | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.45 | 6 | 2 | 28 | 0 | 0.750 | 1.000 | 8 | 2.0 |
| 0.50 | 6 | 2 | 28 | 0 | 0.750 | 1.000 | 8 | 2.0 |
| 0.55 | 6 | 2 | 28 | 0 | 0.750 | 1.000 | 8 | 2.0 |
| 0.35 | 6 | 3 | 27 | 0 | 0.667 | 1.000 | 9 | 3.0 |
| 0.40 | 6 | 3 | 27 | 0 | 0.667 | 1.000 | 9 | 3.0 |
| 0.20 | 6 | 4 | 26 | 0 | 0.600 | 1.000 | 10 | 4.0 |
| 0.25 | 6 | 4 | 26 | 0 | 0.600 | 1.000 | 10 | 4.0 |

Recommended release threshold: **0.45**.

## Probability Calibration

| Probability bin | Rows | Mean predicted probability | Observed escalation rate |
| --- | --- | --- | --- |
| (-0.001, 0.2] | 26 | 0.050 | 0.000 |
| (0.2, 0.4] | 1 | 0.333 | 0.000 |
| (0.4, 0.6] | 2 | 0.521 | 0.500 |
| (0.6, 0.8] | 3 | 0.709 | 0.333 |
| (0.8, 1.0] | 4 | 0.929 | 1.000 |

## Release Decision

The release gate passes only if the model beats the simple baseline on the primary metric, has no catastrophic recall drop on later cohorts, and its chosen threshold keeps review load interpretable. These checks make the model harder to game than a single random holdout score.
