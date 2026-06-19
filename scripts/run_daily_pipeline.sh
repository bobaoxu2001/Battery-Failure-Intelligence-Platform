#!/usr/bin/env bash
#
# run_daily_pipeline.sh - end-to-end Battery Failure Intelligence pipeline.
#
# Steps:
#   1.  Generate / ingest synthetic battery data
#   2.  Parse raw telemetry logs (Perl) + validate files
#   3.  Build modeling features
#   4.  Build the SQL warehouse
#   5.  Train (or reuse) ML models
#   6.  Score all cells and write predictions to the warehouse
#   7.  Run SQL data-quality checks
#   8.  Generate the engineering escalation report
#   9.  Generate Tableau-ready dashboard extracts
#   10. Generate JMP-ready analysis files
#   11. Generate model monitoring summary
#   12. Generate the Markdown model-performance summary
#   13. Generate model-release backtest + survival RUL validation
#   14. Generate public NASA and Oxford real-data validation
#   15. Generate the hiring-manager packet + cell investigation case study
#   16. Generate the project readiness scorecard
#   17. Validate expected output files
#
# Usage:
#   bash scripts/run_daily_pipeline.sh            # full run, reuse models if present
#   RETRAIN=1 bash scripts/run_daily_pipeline.sh  # force model retraining
#   BFI_QUICK=1 bash scripts/run_daily_pipeline.sh # fast smoke-test (small data)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

PY="${PYTHON:-python3}"
RETRAIN="${RETRAIN:-0}"
MODELS_DIR="data/processed/models"
TOTAL_STEPS=17

step() { printf "\n\033[1;34m=== [%s/%s] %s ===\033[0m\n" "$1" "${TOTAL_STEPS}" "$2"; }
models_ready() {
    [[ -f "${MODELS_DIR}/soh_model.joblib" \
        && -f "${MODELS_DIR}/rul_model.joblib" \
        && -f "${MODELS_DIR}/failure_model.joblib" ]]
}
models_need_training() {
    [[ "${RETRAIN}" == "1" ]] && return 0
    models_ready || return 0
    for feature in data/processed/cycle_features.csv data/processed/cell_features.csv; do
        for model in "${MODELS_DIR}/soh_model.joblib" "${MODELS_DIR}/rul_model.joblib" "${MODELS_DIR}/failure_model.joblib"; do
            [[ "${feature}" -nt "${model}" ]] && return 0
        done
    done
    return 1
}

step 1 "Generate + ingest synthetic battery data"
${PY} -m src.ingest.load_raw_data

step 2 "Parse raw telemetry (Perl) + validate files"
if command -v perl >/dev/null 2>&1; then
    LC_ALL=C LANG=C perl scripts/parse_raw_logs.pl data/raw/raw_battery_test_logs.txt data/processed/parsed_raw_logs.csv
else
    echo "  perl not found - skipping raw-log parse (non-fatal)"
fi

step 3 "Build modeling features"
${PY} -m src.features.build_features

step 4 "Build SQL warehouse"
${PY} -m src.warehouse.build_warehouse

step 5 "Train (or reuse) ML models"
if models_need_training; then
    ${PY} -m src.models.train_soh_model
    ${PY} -m src.models.train_rul_model
    ${PY} -m src.models.train_failure_classifier
else
    echo "  Existing models are present and newer than feature tables - reusing"
fi

step 6 "Score all cells and write predictions to warehouse"
${PY} -m src.models.score_cells

step 7 "Run SQL data-quality checks"
${PY} -m src.warehouse.quality_checks

step 8 "Generate engineering escalation report"
${PY} -m src.reporting.generate_escalation_report

step 9 "Generate Tableau-ready dashboard extracts"
${PY} -m src.reporting.generate_tableau_extracts

step 10 "Generate JMP-ready analysis files"
${PY} -m src.reporting.generate_jmp_exports

step 11 "Generate model monitoring summary"
${PY} -m src.models.monitor_drift

step 12 "Generate model-performance summary"
${PY} -m src.models.evaluate_models

step 13 "Generate model-release backtest + survival RUL validation"
${PY} -m src.models.model_release_backtest
${PY} -m src.models.train_survival_rul_model

step 14 "Generate public NASA and Oxford real-data validation"
${PY} -m src.ingest.import_public_battery_data
${PY} -m src.ingest.import_oxford_battery_data

step 15 "Generate hiring-manager packet + cell investigation case study"
${PY} -m src.reporting.generate_hiring_manager_packet

step 16 "Generate project readiness scorecard"
${PY} -m src.reporting.generate_project_scorecard

step 17 "Validate expected output files"
bash scripts/validate_files.sh

printf "\n\033[1;32mPipeline complete.\033[0m Outputs in data/processed/, reports/, dashboards/\n"
