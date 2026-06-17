# Real Public Battery Data Validation

_Generated: 2026-06-17._

This report uses **real public lithium-ion battery aging data** for validation.
It does not use Apple confidential data.

- Source dataset: NASA PCoE Battery Aging Data
- Official upstream: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Adapter used: official NASA .mat archive (authoritative)
- Processed-CSV mirror (fallback): https://github.com/natskiu/Nasa-Battery
- Parsed batteries: B0005, B0006, B0007, B0018
- Parsed cycle rows: 636

## Battery-Level Degradation Summary

| Battery | Cycles | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0005 | 168 | 1.856 | 1.325 | 28.6% | 100 | 41.5 | -0.988 |
| B0006 | 168 | 2.035 | 1.186 | 41.7% | 60 | 42.0 | -0.982 |
| B0007 | 168 | 1.891 | 1.432 | 24.3% | 123 | 42.3 | -0.988 |
| B0018 | 132 | 1.855 | 1.341 | 27.7% | 74 | 38.9 | -0.970 |

## How this is used
The main warehouse/model pipeline remains synthetic and fully reproducible.
This real-data layer is an external sanity check: it verifies that the project can ingest public battery aging data and recover physically sensible degradation trends.
