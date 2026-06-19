# Project Readiness Scorecard

_Generated: 2026-06-20 - evidence-based portfolio review._

| Competency | Status | Evidence | Note |
| --- | --- | --- | --- |
| Python ML functions | PASS | src/models/train_soh_model.py<br>src/models/train_rul_model.py<br>src/models/train_survival_rul_model.py<br>src/models/train_failure_classifier.py<br>src/models/score_cells.py | SOH, RUL, censored survival-style RUL, and failure-risk models train, score, and persist metadata. |
| Battery engineering analytics | PASS | src/ingest/generate_synthetic_battery_data.py<br>data/processed/cell_features.csv<br>reports/high_risk_cells_summary.md | Capacity fade, impedance growth, thermal exposure and EOL logic drive the analysis. |
| Real public battery data validation | PASS | src/ingest/import_public_battery_data.py<br>src/ingest/import_oxford_battery_data.py<br>reports/real_data_validation_summary.md<br>reports/oxford_real_data_validation_summary.md | NASA PCoE plus Oxford public battery-aging adapters validate degradation trends across two real sources. |
| SQL warehouse and data modeling | PASS | sql/create_schema.sql<br>sql/build_marts.sql<br>data/processed/battery_warehouse.db | Star schema facts/dimensions plus cell-health, factory-quality and escalation marts. |
| Large-table data loading | PASS | src/warehouse/build_warehouse.py<br>data/processed/cycles.csv | Cycle facts load through a configurable chunked path for large cycler exports. |
| Unix, Bash and Perl | PASS | scripts/run_daily_pipeline.sh<br>scripts/validate_files.sh<br>scripts/parse_raw_logs.pl | One-command orchestration, validation, and raw telemetry parsing. |
| TCP/IP data-source operations | PASS | scripts/check_data_source_connectivity.sh | Host:port preflight for lab/factory data feeds using Unix network tools. |
| Tableau and JMP handoffs | PASS | dashboards/tableau_extracts/executive_battery_health.csv<br>dashboards/tableau_dashboard_blueprint.md<br>reports/jmp_cell_analysis.csv<br>reports/jmp_battery_analysis.jsl | BI-ready CSV extracts, dashboard blueprint, and JMP CSV/JSL starter analysis. |
| Statistics and value-added analysis | PASS | reports/model_performance_summary.md<br>reports/model_release_backtest.md<br>reports/survival_rul_summary.md<br>reports/model_monitoring_summary.md<br>reports/model_monitoring_metrics.csv | Grouped validation, release backtesting, censored survival RUL, explainability, cohort PSI, and risk mix. |
| Urgent escalation reporting | PASS | reports/escalation_report_sample.csv<br>reports/high_risk_cells_summary.md | Ranked high-risk cell queue with likely root cause and follow-up action. |
| Hiring-manager review packet | PASS | reports/hiring_manager_packet.md<br>reports/cell_investigation_case_study.md<br>reports/real_data_coverage_and_limitations.md | Fast review path plus one concrete cell investigation and a candid data-boundary report. |
| AI-powered reusable workflows | PASS | ai_workflows/anomaly_investigation_skill.md<br>ai_workflows/sql_report_generation_skill.md<br>ai_workflows/model_debugging_workflow.md<br>ai_workflows/escalation_report_assistant.md | Reusable LLM workflows for triage, SQL generation, debugging and report writing. |
| Traceability and verification | PASS | pyproject.toml<br>.github/workflows/ci.yml<br>tests/test_model_outputs.py<br>LICENSE | Project metadata, CI, tests and license are present. |

## Overall Score: 13/13

Verdict: **portfolio-ready** for an engineering analytics portfolio.

This scorecard does not claim proprietary battery experience. It shows the repo has concrete, runnable evidence for data ingestion, ML, SQL, reporting, Unix tooling, BI handoffs, and reusable AI-workflow skills.
