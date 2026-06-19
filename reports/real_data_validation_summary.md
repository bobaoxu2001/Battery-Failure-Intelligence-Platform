# Real Public Battery Data Validation

_Generated: 2026-06-20._

This report uses **real public lithium-ion battery aging data** for validation.
It does not use any confidential or proprietary data.

- Source dataset: NASA PCoE Battery Aging Data
- Official upstream: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Run source mode: official NASA .mat archive
- Adapter used: official NASA .mat archive (authoritative)
- Processed-CSV mirror (fallback): https://github.com/natskiu/Nasa-Battery
- Parsed batteries: B0005, B0006, B0007, B0018
- Number of parsed batteries: 4
- Parsed cycle rows: 636
- Skipped batteries: 0
- Clear capacity-fade validation batteries: 4

## Battery-Level Degradation Summary

| Battery | Discharge cycles | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Mean max discharge temp C | Max discharge temp C | Max charge temp C | Corr(cycle, capacity) | Validation note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0005 | 168 | 1.856 | 1.325 | 28.6% | 100 | 39.8 | 41.5 | 31.2 | -0.988 | Clear capacity-fade validation case. |
| B0006 | 168 | 2.035 | 1.186 | 41.7% | 60 | 39.9 | 42.0 | 32.2 | -0.982 | Clear capacity-fade validation case. |
| B0007 | 168 | 1.891 | 1.432 | 24.3% | 123 | 40.4 | 42.3 | 31.9 | -0.988 | Clear capacity-fade validation case. |
| B0018 | 132 | 1.855 | 1.341 | 27.7% | 74 | 37.7 | 38.9 | 36.2 | -0.970 | Clear capacity-fade validation case. |

## Temperature Summary

| Metric | Max discharge temp C | Max charge temp C |
| --- | --- | --- |
| Mean | 39.6 | 30.0 |
| Min | 36.4 | 23.1 |
| Max | 42.3 | 36.2 |

## Skipped Batteries

No requested batteries were skipped.

## Data-Quality Interpretation

The full archive mode is intentionally broad: it proves the adapter can scan all locally available NASA `.mat` batteries, not that every cell is a clean monotonic fade benchmark.
Cells with increasing capacity, weak/positive cycle-capacity correlation, or very short discharge sequences are retained in the report and labeled for review rather than dropped silently.
For interview discussion, the strongest simple capacity-fade evidence remains the clear fade cases, especially the canonical B0005/B0006/B0007/B0018 cells.

## How this is used
The main warehouse/model pipeline remains synthetic and fully reproducible.
This real-data layer is an external sanity check: it verifies that the project can ingest public battery aging data and recover physically sensible degradation trends.
