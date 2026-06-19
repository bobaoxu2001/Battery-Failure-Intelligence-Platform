# Real-Data Coverage and Limitations

_Generated: 2026-06-20._

This report is generated from the same normalized NASA real-data cycle summary used by `reports/real_data_validation_summary.md`.
It does not use confidential company data, proprietary factory records, field telemetry, or internal failure labels.

## Coverage Snapshot

- Source dataset: NASA PCoE Battery Aging Data
- Official upstream: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Adapter used: official_mat_archive
- Run source mode: official NASA .mat archive
- Number of parsed batteries: 4
- Number of parsed discharge cycles: 636
- Parsed battery IDs: B0005, B0006, B0007, B0018
- Skipped batteries: 0

## Coverage by Battery

| Battery | Discharge cycles | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) | Validation note |
| --- | --- | --- | --- | --- | --- | --- |
| B0005 | 168 | 28.6% | 100 | 41.5 | -0.988 | Clear capacity-fade validation case. |
| B0006 | 168 | 41.7% | 60 | 42.0 | -0.982 | Clear capacity-fade validation case. |
| B0007 | 168 | 24.3% | 123 | 42.3 | -0.988 | Clear capacity-fade validation case. |
| B0018 | 132 | 27.7% | 74 | 38.9 | -0.970 | Clear capacity-fade validation case. |

## Skipped Batteries

No requested batteries were skipped.

## Which Parts Use Real Public Data

- NASA PCoE discharge-cycle capacity and temperature data are used by the real-data validation layer.
- `src/ingest/nasa_mat_parser.py` parses official `.mat` battery files when the archive is present locally.
- `src/ingest/import_public_battery_data.py` normalizes real cycle rows and writes the validation reports.

## Which Parts Remain Synthetic

- The default factory, usage, failure-event, model-training, warehouse, and escalation pipeline remains synthetic and reproducible.
- Lot IDs, station IDs, equipment IDs, field-usage profiles, failure labels, and escalation thresholds are synthetic.
- Synthetic model metrics are implementation checks, not production accuracy claims.

## What NASA Validates Well

- Cycle-level degradation ingestion from public battery-aging files.
- Capacity fade and SOH trend extraction for clear fade cases.
- Temperature feature extraction and cycle-capacity correlation reporting.
- A reproducible adapter pattern for adding large public datasets without committing raw archives.

## What NASA Does Not Validate

- Proprietary factory process behavior, station routing, lot history, or supplier-specific process controls.
- Field usage logs, warranty telemetry, device-level customer usage, or proprietary safety events.
- Proprietary failure labels, engineer-reviewed root causes, or production escalation thresholds.
- Production false-positive rates, missed escalation rates, or operational reviewer workload.

## Production Translation

In a real production environment, this layer would connect to governed internal warehouse tables, then validate by cell group, lot, station, protocol, supplier, and time window.
Failure and escalation labels would need calibration with battery engineers, followed by drift tracking, false-positive review, and backtesting across production periods.
