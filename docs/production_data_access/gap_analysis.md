# Production Data Access Gap Analysis

This repository currently proves the battery analytics workflow with reproducible synthetic data and a separate real public NASA PCoE degradation validation layer. It does not contain proprietary production data, internal company data, restricted system exports, or confidential company records.

## Current Data Categories

| Data category | Current source | Where it lives | Notes |
| --- | --- | --- | --- |
| Synthetic factory data | Local generator | `src/ingest/generate_synthetic_battery_data.py`, `data/processed/factory.csv` after a run | Simulates cells, lots, stations, equipment, and acceptance-test metadata. |
| Synthetic cycle data | Local generator | `data/processed/cycles.csv` after a run | Simulates cycle-level voltage, current, capacity, temperature, resistance, and energy. |
| Synthetic usage data | Local generator | `data/processed/usage.csv` after a run | Simulates usage profiles and thermal/fast-charge exposure. |
| Synthetic failure labels | Local generator | `data/processed/failure_events.csv` after a run | Simulates event types, severity, and escalation flags for modeling. |
| Real public degradation data | NASA PCoE Battery Aging Dataset | `src/ingest/nasa_mat_parser.py`, `src/ingest/import_public_battery_data.py`, reports | Validates public cycle-level degradation ingestion and SOH trend logic. |
| Generated reports and dashboard extracts | Pipeline outputs | `reports/`, `dashboards/tableau_extracts/` | Artifacts generated from synthetic pipeline outputs plus NASA validation reports. |

## What The Project Proves

- The end-to-end analytics architecture works: ingest, feature engineering, warehouse modeling, ML training/scoring, quality checks, reporting, and dashboard exports.
- The feature and model code can operate on realistic battery-shaped tables with cell, cycle, usage, failure, lot, and station concepts.
- The NASA adapter can ingest public real battery aging files and recover capacity/SOH degradation trends for clear fade cases.
- The repo has compliance-conscious boundaries: synthetic production-like data remains labeled synthetic, and real NASA data is labeled public validation data.

## What It Does Not Prove Without Authorized Production Data

- It does not prove accuracy on proprietary factory data, field telemetry, safety records, or internal escalation labels.
- It does not validate real station-to-station process variation, lot genealogy, supplier effects, quality holds, retest outcomes, or engineering dispositions.
- It does not calibrate escalation thresholds against production reviewer workload, false positives, false negatives, or teardown feedback.
- It does not contain or imply access to any internal warehouse, VPN, API, credentials, or confidential systems.

## What A Real Battery Engineering Team Would Likely Need

- Factory cycler and acceptance-test measurements with cell, lot, batch, station, fixture, and protocol context.
- Test station logs and calibration histories for station drift and measurement-quality checks.
- Lot and batch metadata, supplier/material lineage, build dates, process route, and quality hold status.
- Usage telemetry or lab-replay summaries with fast-charge, depth-of-discharge, temperature, and duty-cycle features.
- Failure/event labels, quality holds, engineering dispositions, retest results, teardown findings, and action outcomes.
- Governance metadata: data owner, allowed use case, retention policy, lineage, access approvals, and audit trail.
