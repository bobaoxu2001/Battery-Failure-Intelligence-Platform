# Hiring Manager Review Packet

_Generated: 2026-06-23 - fast review guide for a battery data-science hiring manager._

## First 60 Seconds

This project is strongest when reviewed as an engineering analytics system: battery data ingestion, SQL warehouse, leakage-aware ML, escalation reporting, BI/JMP handoffs, and real public NASA validation with clear limits.

Recommended skim path:

1. Read `docs/interview/PANEL_INTERVIEW_GUIDE.md` for the panel talk track.
2. Read `reports/ad_hoc_200_battery_failure_investigation.md` for the 200-cell pass/fail prompt.
3. Read `reports/cell_investigation_case_study.md` for one concrete escalation investigation.
4. Read `reports/real_data_validation_summary.md` for real NASA battery-aging evidence.
5. Read `reports/nasa_full_archive_local_run_summary.md` for the default-vs-full-archive NASA boundary.
6. Read `reports/real_data_coverage_and_limitations.md` for the honest production boundary.
7. Read `reports/project_readiness_scorecard.md` to map role expectations to files.

## Evidence Map (11/11 Present)

| Proof point | Artifact | Why it matters | Status |
| --- | --- | --- | --- |
| Panel interview guide | `docs/interview/PANEL_INTERVIEW_GUIDE.md` | Concise talk track for the Apple Battery DS panel, including what is real vs synthetic and how not to overclaim. | present |
| 200-cell ad-hoc failure investigation | `reports/ad_hoc_200_battery_failure_investigation.md` | Turns the first-round prompt into a battery engineering analytics plan: label definition, SQL summaries, bias controls, validation, and actions. | present |
| End-to-end runnable pipeline | `scripts/run_daily_pipeline.sh` | Generates data, features, warehouse, models, scores, reports, real-data validation, and file checks. | present |
| Real public battery validation | `reports/real_data_validation_summary.md` | Parses NASA PCoE battery-aging data and reports capacity fade, SOH crossing, temperature, and correlation evidence. | present |
| Honest real-data boundary | `reports/real_data_coverage_and_limitations.md` | Separates real NASA validation from synthetic factory, usage, failure labels, and escalation thresholds. | present |
| NASA full-archive local-run boundary | `reports/nasa_full_archive_local_run_summary.md` | Clarifies that 34 batteries / 2,750 rows / 13 clear fade cases came from an optional local archive run, not the default committed report. | present |
| Battery cell investigation | `reports/cell_investigation_case_study.md` | Shows one escalated cell, peer context, likely driver, and engineering follow-up. | present |
| Model evidence | `reports/model_performance_summary.md` | Summarizes SOH, RUL, failure-risk metrics and explains why synthetic metrics are implementation checks. | present |
| Operational escalation output | `reports/high_risk_cells_summary.md` | Daily queue with risk tiers, likely root causes, and recommended engineering actions. | present |
| SQL warehouse and BI handoff | `dashboards/tableau_extracts/executive_battery_health.csv` | Flat extract from the modeled warehouse, ready for Tableau or another BI surface. | present |
| Production access discipline | `docs/production_data_access/production_validation_plan.md` | Defines authorized-only validation, holdouts, label checks, drift review, and feedback loops. | present |

## What To Ask Me In An Interview

- How I prevented target leakage in cell-level validation and group-rate features.
- Why the synthetic model metrics are treated as implementation checks instead of production accuracy claims.
- How the NASA adapter handles clear fade cases versus protocol windows with increasing capacity or weak correlation.
- How I would validate the same pipeline with authorized factory, usage, quality-hold, retest, and disposition data.
- Which escalation thresholds I would tune with battery engineers before production use.

## What I Would Improve With Team Access

- Replace synthetic factory and usage records with governed read-only production tables.
- Backtest false positives and missed escalations by lot, station, protocol, supplier, and time window.
- Add engineer disposition labels to close the feedback loop from alert to action.
- Serve the daily queue through the team's preferred BI/escalation surface instead of local CSV/Markdown artifacts.

## Boundary

No confidential or proprietary data is used. The default factory/usage/failure pipeline is synthetic, the NASA degradation layer is public, and the production connector is an authorized-only scaffold.
