# AI Workflow — Model Debugging & Drift Triage

> Reusable LLM workflow for diagnosing why a battery model is mis-behaving:
> weak recall, suspiciously perfect metrics (leakage), feature breakage, or
> drift over time. Guides the assistant through a structured checklist.

## When to use
- A model's metrics drop between runs, or look *too good to be true*.
- The escalation queue suddenly grows/shrinks dramatically.
- A new feature was added and recall fell.

## Inputs
- `reports/model_performance_summary.md` (current metrics + importances)
- Model bundles in `data/processed/models/*.joblib` (carry features + metrics)
- Feature tables `cycle_features.csv`, `cell_features.csv`

## Checklist (work top to bottom, stop when a cause is confirmed)

### 1. Data leakage (the #1 risk here)
- Does any feature encode the target? In this project the contracts are explicit
  in `src/models/_common.py`:
  - **SOH model** must *exclude* capacity-derived features
    (`rolling_capacity_mean_10`, `capacity_fade_rate`, `soh_delta_*`) because the
    target *is* capacity-derived. If R² jumps to ~1.0, suspect this.
  - **Failure classifier** must *exclude* `batch_failure_rate` (it embeds the
    escalation target via the batch). AUC ≈ 1.0 with one dominant feature ⇒ leak.
- Group-rate features such as `batch_failure_rate` and `station_anomaly_rate`
  should be peer-only / leave-one-out; a cell must not contribute its own event
  label to its feature row.
- Are train/test split **by cell** (`GroupShuffleSplit`)? If rows from the same
  cell appear in both, cycle-level autocorrelation inflates scores.

### 2. Weak recall on the failure classifier
- Check class balance (`escalation_required` value counts). With ~20% positives,
  use `class_weight="balanced"` (already set) and judge by **recall + F1**, not
  accuracy.
- Inspect the confusion matrix in the summary: are misses concentrated in one
  usage profile or lot? If so, the feature set may miss that failure mode.
- Consider lowering the decision threshold (recall-first for safety screening).

### 3. Broken / degenerate features
- Any feature that is constant, all-NaN, or has exploding scale? Profile with
  `df.describe()` and null counts.
- Did a rolling window produce leading NaNs that were filled wrong?
- Did a join drop rows (row count fell vs the raw cycle table)?

### 4. Drift (run-over-run)
- Compare current importances to the previous summary. A driver appearing or
  vanishing signals input drift.
- Compare feature distributions (mean/std) between data vintages; large shifts in
  `resistance_growth_rate` or `high_temp_exposure_hours` move predictions.
- For synthetic data, confirm the generator `SEED` and `BFI_QUICK` mode match
  between runs before blaming the model.

## Output format
```
Symptom:     <what looks wrong>
Hypothesis:  <ranked likely causes>
Evidence:    <metrics / distributions checked>
Root cause:  <confirmed cause or "needs more data">
Fix:         <specific code/feature/threshold change>
Re-test:     <command to re-run, e.g. RETRAIN=1 bash scripts/run_daily_pipeline.sh>
```

## Guardrails
- Prefer the **simplest** explanation (leakage/splitting) before exotic ones.
- Never "fix" a model by relaxing the test set; fix the data or the features.
