# NASA Full Archive Local Run Summary

This report clarifies the boundary between the committed/default NASA validation
report and an optional local full-archive run.

## Bottom Line

- The committed/default CI-friendly NASA report uses a small real sample:
  B0005, B0006, B0007, and B0018, totaling 636 real discharge cycles.
- The full official NASA PCoE archive run is optional and local. It runs only
  when the raw archive is present on disk.
- The raw NASA archive is large and should not be committed to Git.
- Full-archive counts such as 34 batteries, 2,750 discharge rows, and 13 clear
  capacity-fade validation cases refer to a recorded optional local run, not to
  the default committed report.

## Why The Default Report Is Smaller

Fresh clones and CI need a deterministic report without downloading a roughly
200MB public archive. For that reason, the repo includes a small committed
sample generated from NASA's official `.mat` files. The default report proves
that the adapter can parse real public battery-aging rows and recover capacity
fade for canonical NASA cells.

The smaller default report is the right baseline for GitHub review because it is
fast, auditable, and does not rely on a local archive outside the repository.

## What The Optional Full Archive Run Proves

When the official NASA PCoE archive exists locally at
`data/raw/5. Battery Data Set/`, the adapter can scan all discoverable `.mat`
files:

```bash
SOURCE=archive BATTERIES=all bash scripts/run_real_data_validation.sh
```

A recorded local full-archive run parsed 34 batteries and 2,750 discharge rows,
then labeled 13 batteries as clear capacity-fade validation cases. Those counts
belong to the optional local archive run, not to the default committed report.
Other parsed cells were retained with caution notes when they had short
sequences, increasing capacity versus the first discharge, or weak/positive
cycle-capacity correlation.

That proves broader adapter coverage across the official public archive. It
does not prove proprietary factory behavior, Apple battery behavior, field usage
patterns, or production failure-classifier accuracy.

## What Not To Commit

Do not commit:

- `data/raw/5. Battery Data Set/`
- NASA upstream zip archives or nested `BatteryAgingARC_*.zip` files
- Large extracted `.mat` files
- Proprietary battery archives, internal company data, credentials, or private
  factory/user/failure exports

It is okay to commit small derived reports and the already bundled public sample
when they are useful for reviewer traceability.

## How To Explain This In An Interview

Say:

"The default committed NASA report is intentionally small so CI and a fresh
clone stay fast. I also documented the optional full-archive run: when the
official NASA archive is present locally, the adapter can scan 34 batteries and
2,750 discharge rows. Those numbers are public-data adapter coverage, not a
claim about Apple production accuracy."

## Boundary

NASA validates real public degradation parsing and SOH trend extraction. It does
not validate factory lot effects, station issues, field telemetry, quality holds,
engineer dispositions, teardown outcomes, or production escalation thresholds.
