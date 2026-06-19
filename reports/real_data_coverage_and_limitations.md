# Real-Data Coverage and Limitations

_Generated: 2026-06-19._

This report is generated from the same normalized NASA real-data cycle summary used by `reports/real_data_validation_summary.md`.
It does not use Apple confidential data, proprietary factory records, field telemetry, or internal failure labels.

## Coverage Snapshot

- Source dataset: NASA PCoE Battery Aging Data
- Official upstream: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Adapter used: official_mat_archive
- Run source mode: official NASA .mat archive
- Number of parsed batteries: 34
- Number of parsed discharge cycles: 2750
- Parsed battery IDs: B0005, B0006, B0007, B0018, B0025, B0026, B0027, B0028, B0029, B0030, B0031, B0032, B0033, B0034, B0036, B0038, B0039, B0040, B0041, B0042, B0043, B0044, B0045, B0046, B0047, B0048, B0049, B0050, B0051, B0052, B0053, B0054, B0055, B0056
- Skipped batteries: 0

## Coverage by Battery

| Battery | Discharge cycles | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) | Validation note |
| --- | --- | --- | --- | --- | --- | --- |
| B0005 | 168 | 28.6% | 100 | 41.5 | -0.988 | Clear capacity-fade validation case. |
| B0006 | 168 | 41.7% | 60 | 42.0 | -0.982 | Clear capacity-fade validation case. |
| B0007 | 168 | 24.3% | 123 | 42.3 | -0.988 | Clear capacity-fade validation case. |
| B0018 | 132 | 27.7% | 74 | 38.9 | -0.970 | Clear capacity-fade validation case. |
| B0025 | 28 | 4.3% |  | 41.8 | -0.938 | Parsed real cycle data; limited fade signal in this window. |
| B0026 | 28 | 2.5% | 5 | 40.9 | 0.038 | Parsed real cycle data; limited fade signal in this window. |
| B0027 | 28 | 2.9% |  | 43.2 | -0.700 | Parsed real cycle data; limited fade signal in this window. |
| B0028 | 28 | 4.8% |  | 32.5 | -0.942 | Parsed real cycle data; limited fade signal in this window. |
| B0029 | 40 | 5.0% |  | 60.3 | -0.930 | Clear capacity-fade validation case. |
| B0030 | 40 | 5.6% |  | 63.0 | -0.938 | Clear capacity-fade validation case. |
| B0031 | 40 | -0.0% |  | 62.1 | -0.822 | Slight capacity gain versus first discharge; use cautiously. |
| B0032 | 40 | 4.1% |  | 63.0 | -0.909 | Parsed real cycle data; limited fade signal in this window. |
| B0033 | 197 | -1822.2% |  | 61.1 | -0.359 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0034 | 197 | -71.6% |  | 61.4 | -0.585 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0036 | 197 | -55.6% |  | 39.4 | -0.545 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0038 | 47 | -70.4% |  | 69.9 | 0.686 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0039 | 47 | -1005.0% |  | 64.1 | 0.678 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0040 | 47 | 17.3% | 45 | 55.7 | 0.479 | Positive capacity trend; not a simple capacity-fade validation case. |
| B0041 | 67 | -1403.9% | 5 | 14.8 | 0.799 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0042 | 111 | 22.6% | 40 | 41.7 | -0.310 | Parsed real cycle data; limited fade signal in this window. |
| B0043 | 111 | 25.5% | 40 | 38.1 | -0.290 | Parsed real cycle data; limited fade signal in this window. |
| B0044 | 111 | 26.0% | 40 | 39.1 | -0.294 | Parsed real cycle data; limited fade signal in this window. |
| B0045 | 70 | 43.9% | 3 | 16.9 | -0.879 | Clear capacity-fade validation case. |
| B0046 | 69 | 33.2% | 17 | 15.4 | -0.908 | Clear capacity-fade validation case. |
| B0047 | 69 | 30.9% | 17 | 13.2 | -0.862 | Clear capacity-fade validation case. |
| B0048 | 69 | 26.2% | 20 | 11.6 | -0.828 | Clear capacity-fade validation case. |
| B0049 | 24 | 19.5% |  | 22.6 | -0.636 | Clear capacity-fade validation case. |
| B0050 | 20 | 67.8% | 4 | 25.0 | -0.549 | Clear capacity-fade validation case. |
| B0051 | 24 | -5.3% |  | 20.7 | -0.543 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0052 | 4 | -57.0% |  | 16.4 | 0.704 | Very short discharge sequence; useful for parser coverage only. |
| B0053 | 55 | 5.5% |  | 22.1 | -0.554 | Clear capacity-fade validation case. |
| B0054 | 102 | -13.2% |  | 25.4 | -0.821 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0055 | 102 | -24.0% |  | 20.3 | -0.687 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0056 | 102 | -43.8% |  | 15.7 | -0.446 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |

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

- Apple factory process behavior, station routing, lot history, or supplier-specific process controls.
- Field usage logs, warranty telemetry, device-level customer usage, or proprietary safety events.
- Apple proprietary failure labels, engineer-reviewed root causes, or production escalation thresholds.
- Production false-positive rates, missed escalation rates, or operational reviewer workload.

## Production Translation

In a real production environment, this layer would connect to governed internal warehouse tables, then validate by cell group, lot, station, protocol, supplier, and time window.
Failure and escalation labels would need calibration with battery engineers, followed by drift tracking, false-positive review, and backtesting across production periods.
