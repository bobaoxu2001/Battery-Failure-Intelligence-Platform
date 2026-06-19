# Real-Data Coverage and Limitations

This project uses public real battery data only as an external validation layer. It does not use Apple confidential data, proprietary factory records, field telemetry, or internal failure labels.

## What Is Real Public Data

- `src/ingest/nasa_mat_parser.py` reads the official NASA PCoE Battery Aging Dataset MATLAB files when the archive is present locally under `data/raw/5. Battery Data Set/`.
- `src/ingest/import_public_battery_data.py` normalizes discharge-cycle capacity, SOH, remaining-cycle targets, temperature summaries, and voltage/temperature slopes into `data/processed/nasa_real_cycle_summary.csv`.
- `reports/real_data_validation_summary.md` is generated from real NASA discharge cycles. In the current local full-archive run, it parsed 34 batteries and 2,750 discharge-cycle rows. The committed CI-safe sample remains limited to B0005/B0006/B0007/B0018.

## What Remains Synthetic

- The default end-to-end factory, usage, and failure-event pipeline is synthetic and reproducible by design.
- Factory lots, stations, equipment IDs, manufacturing dates, usage profiles, failure events, escalation labels, and production-style thresholds are synthetic.
- The SOH, RUL, and failure-risk model metrics in `reports/model_performance_summary.md` are synthetic-pipeline metrics. They prove the modeling path works; they are not production accuracy claims.

## What NASA Validates Well

- Cycle-level degradation ingestion from public `.mat` battery-aging files.
- Capacity fade and SOH trend extraction for clear fade cases such as B0005, B0006, B0007, and B0018.
- First cycle below 80% SOH, cycle-capacity correlation, and temperature-summary reporting.
- A reproducible adapter pattern for adding more public battery datasets without committing large raw data.

## What NASA Does Not Validate

- Apple factory processes, station behavior, lot history, or internal test routing.
- Real customer field usage, device telemetry, warranty events, or safety escalations.
- Proprietary failure labels, engineer-reviewed root causes, or production escalation thresholds.
- Production drift, false escalation cost, or calibration against internal engineering decisions.

## Full-Archive Interpretation

The `--all-available` path intentionally parses every NASA battery discoverable in the local archive. Not every parsed cell is a clean monotonic capacity-fade benchmark. Some batteries have short discharge sequences, increasing capacity relative to the first discharge, or weak/positive cycle-capacity correlation. The report keeps those rows and labels them instead of silently dropping them.

That gives two honest claims:

- Coverage claim: the adapter can scan the official local archive and summarize every available battery file.
- Validation claim: clear fade cases validate the SOH and degradation ingestion logic; anomalous or short sequences require protocol review before being used for model training.

## Production-Readiness Translation

In a real Apple-style battery analytics environment, this same structure would need to connect to internal governed data sources:

- Internal cycler, factory, MES, reliability, and field-usage warehouse tables.
- Validation by cell group, lot, station, protocol, supplier, firmware/software version, and time window.
- Label calibration with battery engineers so failure labels and escalation thresholds match real review outcomes.
- Backtesting by production period to estimate false escalations, missed escalations, and reviewer workload.
- Drift monitoring for process changes, protocol changes, new suppliers, and new cell designs.
- Clear data contracts for confidential sources, access controls, retention rules, and audit trails.

## Interview Wording

Use this wording if challenged:

> The project has a deterministic synthetic pipeline for factory, usage, and failure analytics, plus a separate public NASA validation layer for real cycle-level degradation. The NASA data validates that my ingestion and SOH trend logic work on real battery aging files, but it does not validate Apple factory processes or proprietary failure labels. In production I would connect this same pipeline shape to internal warehouse tables, calibrate labels with battery engineers, and monitor drift and false escalations over time.
