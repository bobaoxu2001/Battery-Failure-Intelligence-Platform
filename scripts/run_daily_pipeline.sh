#!/usr/bin/env bash
#
# run_daily_pipeline.sh - end-to-end Battery Failure Intelligence pipeline.
#
# Steps:
#   1.  Generate / ingest synthetic battery data
#   2.  Parse raw telemetry logs (Perl) + validate files
#   3.  Build the SQL warehouse
#   4.  Run SQL data-quality checks
#   5.  Build modeling features
#   6.  Train (or reuse) ML models
#   7.  Score all cells
#   8.  Write predictions to the warehouse (done within scoring)
#   9.  Generate the engineering escalation report
#   10. Generate Tableau-ready dashboard extracts
#   11. Generate the Markdown model-performance summary
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

step() { printf "\n\033[1;34m=== [%s/11] %s ===\033[0m\n" "$1" "$2"; }

step 1 "Generate + ingest synthetic battery data"
${PY} -m src.ingest.load_raw_data

step 2 "Parse raw telemetry (Perl) + validate files"
if command -v perl >/dev/null 2>&1; then
    perl scripts/parse_raw_logs.pl data/raw/raw_battery_test_logs.txt data/processed/parsed_raw_logs.csv
else
    echo "  perl not found - skipping raw-log parse (non-fatal)"
fi

step 3 "Build SQL warehouse"
${PY} -m src.warehouse.build_warehouse

step 4 "Run SQL data-quality checks"
${PY} -m src.warehouse.quality_checks

step 5 "Build modeling features"
${PY} -m src.features.build_features

step 6 "Train (or reuse) ML models"
if [[ "${RETRAIN}" == "1" || ! -f "${MODELS_DIR}/soh_model.joblib" ]]; then
    ${PY} -m src.models.train_soh_model
    ${PY} -m src.models.train_rul_model
    ${PY} -m src.models.train_failure_classifier
else
    echo "  Existing models found - reusing (set RETRAIN=1 to force retrain)"
fi

step 7 "Score all cells (8. writes predictions to warehouse)"
${PY} -m src.models.score_cells

step 9 "Generate engineering escalation report"
${PY} -m src.reporting.generate_escalation_report

step 10 "Generate Tableau-ready dashboard extracts"
${PY} -m src.reporting.generate_tableau_extracts

step 11 "Generate model-performance summary"
${PY} -m src.models.evaluate_models

echo
echo "==> Final file validation"
bash scripts/validate_files.sh

printf "\n\033[1;32mPipeline complete.\033[0m Outputs in data/processed/, reports/, dashboards/\n"
