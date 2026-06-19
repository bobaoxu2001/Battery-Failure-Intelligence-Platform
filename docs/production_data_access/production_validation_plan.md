# Production Validation Plan

This plan describes how the SOH, RUL, and failure-risk models would be evaluated if authorized production data became available.

## 1. Data Readiness

- Confirm that factory tests, cycle measurements, usage summaries, failure events, quality holds, station calibration logs, and engineering dispositions are available for the approved scope.
- Verify table grain, primary keys, timestamp semantics, and lineage fields against `production_data_contract.md`.
- Separate raw observations, engineered features, model predictions, and engineer-reviewed outcomes.

## 2. Train/Test Splits

- Use a time-based split so validation periods occur after training periods.
- Use cell-grouped validation so all cycles and events for a cell stay on one side of the split.
- Add lot, station, supplier, and protocol holdouts to evaluate generalization across manufacturing/process cohorts.
- Reserve a recent untouched backtest window for final threshold calibration.

## 3. Leakage Checks

- Confirm that failure labels, quality holds, engineering dispositions, and escalation outcomes are not used as pre-event model features.
- Recompute group-rate features using leave-one-out or historical-only windows.
- Ensure feature timestamps precede label timestamps.
- Validate that retest/teardown outcomes are used only for evaluation or later feedback loops, not initial prediction features.

## 4. Label Quality Review

- Review failure-event definitions with battery engineers.
- Distinguish measured degradation, engineer disposition, quality hold, model alert, and confirmed root cause.
- Quantify disagreement between automated labels and engineer-reviewed labels.
- Track unknown, pending, and ambiguous outcomes instead of forcing them into binary labels.

## 5. Model Evaluation

- Report SOH/RUL error by cell group, lot, station, protocol, and time window.
- Report failure-risk precision, recall, ROC-AUC, PR-AUC, false positives, and false negatives.
- Review top drivers and case examples with engineers before production use.
- Compare model alerts with quality holds, retest results, teardown findings, and final dispositions.

## 6. Threshold Calibration

- Calibrate escalation thresholds against reviewer capacity and risk tolerance.
- Measure false-positive review burden and false-negative miss cost.
- Use separate thresholds by product family, protocol, or operating regime only if justified by validation data.
- Require approval before any threshold drives production action.

## 7. Drift Monitoring

- Track input feature drift by lot, station, protocol, supplier, time window, and cell group.
- Track prediction drift and alert-rate drift.
- Monitor label drift when test protocols, product designs, or failure review practices change.
- Trigger retraining/review when drift exceeds agreed thresholds.

## 8. Feedback Loop

- Feed retest, teardown, disposition, and quality-action outcomes back into offline validation datasets.
- Maintain versioned feature snapshots and model predictions.
- Review false positives and false negatives with engineers on a regular cadence.
- Document every model or threshold change with lineage, validation results, and approval status.
