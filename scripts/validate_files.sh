#!/usr/bin/env bash
#
# validate_files.sh - sanity-check that the pipeline produced its expected
# outputs and that key CSVs are non-empty. Prints friendly per-file messages and
# exits non-zero if anything required is missing/empty (so CI can gate on it).
#
# Usage: bash scripts/validate_files.sh

set -uo pipefail

# Resolve repo root from this script's location so it works from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
fail_count=0

# check_file <path> <min_lines> <required|optional>
check_file() {
    local path="$1" min_lines="${2:-1}" mode="${3:-required}"
    if [[ ! -f "${path}" ]]; then
        if [[ "${mode}" == "optional" ]]; then
            printf "${YELLOW}  ~ SKIP${NC} %s (optional, not present)\n" "${path}"
        else
            printf "${RED}  x MISSING${NC} %s\n" "${path}"
            ((fail_count++))
        fi
        return
    fi
    local lines
    lines=$(wc -l < "${path}" | tr -d ' ')
    if (( lines < min_lines )); then
        printf "${RED}  x EMPTY${NC} %s (%s lines, need >= %s)\n" "${path}" "${lines}" "${min_lines}"
        ((fail_count++))
    else
        printf "${GREEN}  ok${NC} %-52s (%s lines)\n" "${path}" "${lines}"
    fi
}

echo "==> Validating processed data"
check_file "data/processed/factory.csv"        2
check_file "data/processed/cycles.csv"         100
check_file "data/processed/usage.csv"          2
check_file "data/processed/failure_events.csv" 2
check_file "data/processed/parsed_raw_logs.csv" 2
check_file "data/processed/cycle_features.csv" 100
check_file "data/processed/cell_features.csv"  2
check_file "data/public_samples/nasa_real_cycle_summary_sample.csv" 100
check_file "data/public_samples/oxford_real_cycle_summary_sample.csv" 10
check_file "data/processed/nasa_real_cycle_summary.csv" 100
check_file "data/processed/oxford_real_cycle_summary.csv" 10

echo "==> Validating warehouse + model artifacts"
check_file "data/processed/battery_warehouse.db" 1
check_file "data/processed/model_predictions.csv" 2
check_file "data/processed/models/soh_model.joblib"     1
check_file "data/processed/models/rul_model.joblib"     1
check_file "data/processed/models/failure_model.joblib" 1
check_file "data/processed/models/survival_rul_model.joblib" 1

echo "==> Validating reports + dashboard extracts"
check_file "reports/escalation_report_sample.csv"      1
check_file "reports/high_risk_cells_summary.md"        3
check_file "reports/model_performance_summary.md"      3
check_file "reports/model_release_backtest.md"         3
check_file "reports/model_release_backtest_metrics.csv" 2
check_file "reports/model_release_calibration.csv"     2
check_file "reports/survival_rul_summary.md"           3
check_file "reports/survival_rul_predictions.csv"      2
check_file "reports/model_monitoring_summary.md"       3
check_file "reports/model_monitoring_metrics.csv"      2
check_file "reports/project_readiness_scorecard.md"    3
check_file "reports/hiring_manager_packet.md"          3
check_file "reports/cell_investigation_case_study.md"  3
check_file "reports/real_data_validation_summary.md"   3
check_file "reports/real_data_coverage_and_limitations.md" 3
check_file "reports/oxford_real_data_validation_summary.md" 3
check_file "reports/jmp_cell_analysis.csv"             2
check_file "reports/jmp_battery_analysis.jsl"          3
check_file "dashboards/tableau_extracts/executive_battery_health.csv" 2
check_file "dashboards/tableau_extracts/factory_lot_quality.csv"      2
check_file "dashboards/tableau_extracts/engineering_root_cause.csv"   2
check_file "dashboards/tableau_extracts/escalation_queue.csv"         1

echo
if (( fail_count > 0 )); then
    printf "${RED}Validation FAILED: %d problem(s).${NC}\n" "${fail_count}"
    exit 1
fi
printf "${GREEN}All required files present and non-empty.${NC}\n"
