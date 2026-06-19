#!/usr/bin/env bash
#
# run_real_data_validation.sh - import public real NASA battery aging data and
# generate a validation report. This is intentionally separate from the daily
# synthetic pipeline so CI and first-run demos do not depend on external network
# speed or third-party mirrors.
#
# Usage:
#   bash scripts/run_real_data_validation.sh                  # auto source
#   SOURCE=archive bash scripts/run_real_data_validation.sh   # force official .mat archive
#   SOURCE=archive BATTERIES=all bash scripts/run_real_data_validation.sh
#   DOWNLOAD=1 bash scripts/run_real_data_validation.sh       # fetch processed-CSV mirror

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

PY="${PYTHON:-python3}"
DOWNLOAD="${DOWNLOAD:-0}"
SOURCE="${SOURCE:-auto}"
BATTERIES="${BATTERIES:-}"

args=(--source "${SOURCE}")
if [[ "${DOWNLOAD}" == "1" ]]; then
    args+=(--download)
fi
if [[ "${BATTERIES}" == "all" ]]; then
    args+=(--all-available)
elif [[ -n "${BATTERIES}" ]]; then
    IFS=',' read -ra battery_ids <<< "${BATTERIES}"
    for battery_id in "${battery_ids[@]}"; do
        battery_id="${battery_id//[[:space:]]/}"
        [[ -n "${battery_id}" ]] && args+=(--battery-id "${battery_id}")
    done
fi

# Expand safely under `set -u` on bash 3.2 (macOS default).
${PY} -m src.ingest.import_public_battery_data ${args[@]+"${args[@]}"}

printf "\nReal-data validation complete:\n"
printf "  data/processed/nasa_real_cycle_summary.csv\n"
printf "  reports/real_data_validation_summary.md\n"
