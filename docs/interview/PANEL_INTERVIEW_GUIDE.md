# Apple Battery DS Panel Interview Guide

This guide is for a fast technical panel skim. It explains how to present this
repo as an engineering analytics portfolio without implying Apple, internal, or
production data access.

## 60-Second Project Summary

This project answers a battery reliability question: if a group of tested cells
has failures, how do we move from raw cycler/factory-style data to a defensible
engineering investigation?

The repo demonstrates a local analytics system: synthetic production-style cell
data, feature engineering, SQL warehouse tables, leakage-aware SOH/RUL/failure
models, ranked escalation reports, Tableau/JMP handoffs, public NASA/Oxford
battery-aging validation, and documented production-data guardrails. The main
claim is workflow readiness and traceability, not production accuracy.

## How It Maps To The Battery Data Scientist Contractor Role

| Role need | Repo evidence | Interview angle |
| --- | --- | --- |
| Battery data analysis | `reports/ad_hoc_200_battery_failure_investigation.md`, `reports/cell_investigation_case_study.md` | Shows pass/fail comparison, bias checks, interpretable modeling, and engineering actions. |
| Python analytics | `src/features/`, `src/models/`, `src/reporting/` | Modular Python pipeline from ingestion to reports. |
| SQL and data modeling | `sql/create_schema.sql`, `sql/build_marts.sql`, `sql/example_ad_hoc_queries.sql` | Star schema, marts, quality checks, and ad-hoc engineering queries. |
| GitHub traceability | `.github/workflows/ci.yml`, `tests/`, generated reports | Work is reviewable, tested, and tied to concrete artifacts. |
| Tableau/JMP handoff | `dashboards/tableau_extracts/`, `reports/jmp_cell_analysis.csv`, `reports/jmp_battery_analysis.jsl` | Analysts and engineers can inspect results outside Python. |
| Bash/Perl/Unix | `scripts/run_daily_pipeline.sh`, `scripts/parse_raw_logs.pl`, `scripts/validate_files.sh` | Practical local orchestration and log parsing. |
| AI-assisted workflows | `ai_workflows/` | Reusable prompts for SQL generation, anomaly triage, report writing, and debugging. |
| Urgent ad-hoc reporting | `reports/high_risk_cells_summary.md`, `reports/ad_hoc_200_battery_failure_investigation.md` | Turns a vague failure question into a structured engineering plan. |

## What Is Real Vs Synthetic

| Layer | Status | How to state it |
| --- | --- | --- |
| Factory, usage, failure labels, warehouse, model training | Synthetic production-style data | "I built this to demonstrate the workflow without using proprietary data." |
| NASA PCoE battery aging validation | Public real data | "This validates degradation parsing and SOH trend extraction, not factory failure accuracy." |
| Oxford battery aging validation | Public real data | "This is a second public dataset adapter for degradation sanity checks." |
| Production data access | Authorized-only scaffold | "The repo defines contracts and validation plans, but does not connect to private systems." |
| Apple or internal data | Not used | "No Apple data, credentials, factory exports, or internal production records are present." |

## How To Explain It Without Overclaiming

- Say: "I have not worked with Apple production battery data in this repo."
- Say: "The synthetic layer lets me show the analytics system end to end."
- Say: "The NASA/Oxford layer proves I can parse real battery-aging data and recover physical degradation signals."
- Say: "Production accuracy would require authorized factory, usage, failure, retest, teardown, quality-hold, and disposition data."
- Avoid: "This model is production-ready for Apple batteries."
- Avoid: "The failure classifier accuracy represents real-world manufacturing performance."

## Likely Panel Questions And Strong Answer Bullets

### If 200 cells were tested and 20 failed, what would you do first?

- Define the exact failure label and whether retest/disposition changes it.
- Build a cell-level table with pass/fail status and pre-failure features.
- Compare pass vs fail by lot, station, protocol, equipment, time window, temperature, and resistance/impedance before ML.
- Check whether the 20 failures cluster in one lot, station, fixture, operator shift, protocol, or environmental condition.
- Turn the first result into engineering actions: retest, station calibration check, teardown, lot hold, or supplier/process review.

### Why not start with a complex model?

- With only 20 failed cells, grouped summaries and interpretable baselines are more reliable than a black-box model.
- I would start with SQL summaries, confidence intervals, simple logistic regression, and shallow decision trees.
- More complex ML is useful later only if the label definition, leakage boundary, and validation splits are clean.

### How do you prevent leakage?

- Keep post-failure fields such as teardown, engineer disposition, quality hold, and retest outcome out of pre-failure features.
- Recompute group-rate features using historical-only or leave-one-out logic.
- Split by cell, time, lot, station, or protocol depending on the question.
- Confirm every feature timestamp precedes the label timestamp.

### What would you need from an internal battery team?

- Failure definition, test protocol, retest rules, and engineer disposition taxonomy.
- Factory test records, lot/batch genealogy, station/equipment logs, cycle summaries, temperature exposure, impedance/resistance, quality holds, teardown results, and final actions.
- Review capacity from engineers so escalation thresholds can be calibrated to real workflow cost.

### What does the public NASA layer prove?

- The adapter can parse real public battery-aging data and recover capacity fade, SOH crossing, temperature, and cycle-capacity correlation.
- It does not prove proprietary factory failure modes or production escalation accuracy.
- The committed/default report uses a small CI-friendly real sample; the full official NASA archive run is optional and local.

## Recommended Files To Skim First

1. `reports/ad_hoc_200_battery_failure_investigation.md`
2. `reports/hiring_manager_packet.md`
3. `reports/cell_investigation_case_study.md`
4. `reports/real_data_validation_summary.md`
5. `reports/nasa_full_archive_local_run_summary.md`
6. `reports/real_data_coverage_and_limitations.md`
7. `reports/project_readiness_scorecard.md`
8. `docs/production_data_access/production_validation_plan.md`
9. `sql/example_ad_hoc_queries.sql`
10. `scripts/run_daily_pipeline.sh`
