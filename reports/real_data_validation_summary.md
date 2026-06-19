# Real Public Battery Data Validation

_Generated: 2026-06-19._

This report uses **real public lithium-ion battery aging data** for validation.
It does not use any confidential or proprietary data.

- Source dataset: NASA PCoE Battery Aging Data
- Official upstream: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Run source mode: official NASA .mat archive
- Adapter used: official NASA .mat archive (authoritative)
- Processed-CSV mirror (fallback): https://github.com/natskiu/Nasa-Battery
- Parsed batteries: B0005, B0006, B0007, B0018, B0025, B0026, B0027, B0028, B0029, B0030, B0031, B0032, B0033, B0034, B0036, B0038, B0039, B0040, B0041, B0042, B0043, B0044, B0045, B0046, B0047, B0048, B0049, B0050, B0051, B0052, B0053, B0054, B0055, B0056
- Number of parsed batteries: 34
- Parsed cycle rows: 2750
- Skipped batteries: 0
- Clear capacity-fade validation batteries: 13

## Battery-Level Degradation Summary

| Battery | Discharge cycles | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Mean max discharge temp C | Max discharge temp C | Max charge temp C | Corr(cycle, capacity) | Validation note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0005 | 168 | 1.856 | 1.325 | 28.6% | 100 | 39.8 | 41.5 | 31.2 | -0.988 | Clear capacity-fade validation case. |
| B0006 | 168 | 2.035 | 1.186 | 41.7% | 60 | 39.9 | 42.0 | 32.2 | -0.982 | Clear capacity-fade validation case. |
| B0007 | 168 | 1.891 | 1.432 | 24.3% | 123 | 40.4 | 42.3 | 31.9 | -0.988 | Clear capacity-fade validation case. |
| B0018 | 132 | 1.855 | 1.341 | 27.7% | 74 | 37.7 | 38.9 | 36.2 | -0.970 | Clear capacity-fade validation case. |
| B0025 | 28 | 1.847 | 1.768 | 4.3% |  | 41.0 | 41.8 | 36.8 | -0.938 | Parsed real cycle data; limited fade signal in this window. |
| B0026 | 28 | 1.813 | 1.769 | 2.5% | 5 | 40.5 | 40.9 | 36.6 | 0.038 | Parsed real cycle data; limited fade signal in this window. |
| B0027 | 28 | 1.823 | 1.770 | 2.9% |  | 42.6 | 43.2 | 38.1 | -0.700 | Parsed real cycle data; limited fade signal in this window. |
| B0028 | 28 | 1.805 | 1.717 | 4.8% |  | 31.8 | 32.5 | 32.0 | -0.942 | Parsed real cycle data; limited fade signal in this window. |
| B0029 | 40 | 1.698 | 1.612 | 5.0% |  | 60.0 | 60.3 | 59.0 | -0.930 | Clear capacity-fade validation case. |
| B0030 | 40 | 1.656 | 1.563 | 5.6% |  | 62.5 | 63.0 | 59.6 | -0.938 | Clear capacity-fade validation case. |
| B0031 | 40 | 1.667 | 1.667 | -0.0% |  | 61.7 | 62.1 | 61.0 | -0.822 | Slight capacity gain versus first discharge; use cautiously. |
| B0032 | 40 | 1.705 | 1.636 | 4.1% |  | 61.8 | 63.0 | 59.9 | -0.909 | Parsed real cycle data; limited fade signal in this window. |
| B0033 | 197 | 0.068 | 1.315 | -1822.2% |  | 53.4 | 61.1 | 31.8 | -0.359 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0034 | 197 | 0.746 | 1.280 | -71.6% |  | 57.1 | 61.4 | 31.4 | -0.585 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0036 | 197 | 1.002 | 1.559 | -55.6% |  | 35.5 | 39.4 | 38.6 | -0.545 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0038 | 47 | 0.898 | 1.530 | -70.4% |  | 51.0 | 69.9 | 54.1 | 0.686 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0039 | 47 | 0.119 | 1.315 | -1005.0% |  | 48.3 | 64.1 | 50.6 | 0.678 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0040 | 47 | 0.673 | 0.557 | 17.3% | 45 | 46.9 | 55.7 | 49.3 | 0.479 | Positive capacity trend; not a simple capacity-fade validation case. |
| B0041 | 67 | 0.056 | 0.836 | -1403.9% | 5 | 11.6 | 14.8 | 10.3 | 0.799 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0042 | 111 | 1.729 | 1.337 | 22.6% | 40 | 30.0 | 41.7 | 39.4 | -0.310 | Parsed real cycle data; limited fade signal in this window. |
| B0043 | 111 | 1.714 | 1.277 | 25.5% | 40 | 19.7 | 38.1 | 35.7 | -0.290 | Parsed real cycle data; limited fade signal in this window. |
| B0044 | 111 | 1.687 | 1.249 | 26.0% | 40 | 19.8 | 39.1 | 34.9 | -0.294 | Parsed real cycle data; limited fade signal in this window. |
| B0045 | 70 | 1.082 | 0.607 | 43.9% | 3 | 15.9 | 16.9 | 9.9 | -0.879 | Clear capacity-fade validation case. |
| B0046 | 69 | 1.728 | 1.154 | 33.2% | 17 | 14.2 | 15.4 | 14.5 | -0.908 | Clear capacity-fade validation case. |
| B0047 | 69 | 1.674 | 1.157 | 30.9% | 17 | 12.1 | 13.2 | 11.2 | -0.862 | Clear capacity-fade validation case. |
| B0048 | 69 | 1.658 | 1.223 | 26.2% | 20 | 10.8 | 11.6 | 10.8 | -0.828 | Clear capacity-fade validation case. |
| B0049 | 24 | 0.858 | 0.691 | 19.5% |  | 20.4 | 22.6 | 20.8 | -0.636 | Clear capacity-fade validation case. |
| B0050 | 20 | 0.863 | 0.278 | 67.8% | 4 | 17.0 | 25.0 | 23.6 | -0.549 | Clear capacity-fade validation case. |
| B0051 | 24 | 0.643 | 0.678 | -5.3% |  | 17.9 | 20.7 | 13.0 | -0.543 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0052 | 4 | 0.861 | 1.352 | -57.0% |  | 15.9 | 16.4 | 8.6 | 0.704 | Very short discharge sequence; useful for parser coverage only. |
| B0053 | 55 | 1.069 | 1.010 | 5.5% |  | 20.4 | 22.1 | 21.1 | -0.554 | Clear capacity-fade validation case. |
| B0054 | 102 | 0.740 | 0.837 | -13.2% |  | 22.4 | 25.4 | 24.0 | -0.821 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0055 | 102 | 0.799 | 0.991 | -24.0% |  | 17.7 | 20.3 | 13.1 | -0.687 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |
| B0056 | 102 | 0.785 | 1.129 | -43.8% |  | 14.3 | 15.7 | 10.6 | -0.446 | Capacity increases versus first discharge; review protocol/first-cycle normalization before fade modeling. |

## Temperature Summary

| Metric | Max discharge temp C | Max charge temp C |
| --- | --- | --- |
| Mean | 34.6 | 25.6 |
| Min | 6.9 | 6.1 |
| Max | 69.9 | 61.0 |

## Skipped Batteries

No requested batteries were skipped.

## Data-Quality Interpretation

The full archive mode is intentionally broad: it proves the adapter can scan all locally available NASA `.mat` batteries, not that every cell is a clean monotonic fade benchmark.
Cells with increasing capacity, weak/positive cycle-capacity correlation, or very short discharge sequences are retained in the report and labeled for review rather than dropped silently.
For interview discussion, the strongest simple capacity-fade evidence remains the clear fade cases, especially the canonical B0005/B0006/B0007/B0018 cells.

## How this is used
The main warehouse/model pipeline remains synthetic and fully reproducible.
This real-data layer is an external sanity check: it verifies that the project can ingest public battery aging data and recover physically sensible degradation trends.
