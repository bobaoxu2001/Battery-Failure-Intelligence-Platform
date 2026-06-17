#!/usr/bin/env bash
#
# sql_export.sh - run the example ad-hoc engineering queries against the
# warehouse and export each result to a CSV (handy for sharing or Tableau).
# Demonstrates a Unix-style sqlite3 + here-doc reporting workflow.
#
# Usage: bash scripts/sql_export.sh [OUTPUT_DIR]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

DB="data/processed/battery_warehouse.db"
OUT_DIR="${1:-reports/sql_exports}"
mkdir -p "${OUT_DIR}"

if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "sqlite3 CLI not found; using Python fallback for exports."
    python3 - "$DB" "$OUT_DIR" <<'PY'
import sqlite3, sys, pandas as pd
db, out = sys.argv[1], sys.argv[2]
queries = {
    "lots_highest_risk": "SELECT lot_id, ROUND(AVG(escalation_rate),4) r FROM mart_factory_quality GROUP BY lot_id ORDER BY r DESC LIMIT 10",
    "stations_abnormal": "SELECT station_id, ROUND(AVG(thermal_anomaly_rate),4) t FROM mart_factory_quality GROUP BY station_id ORDER BY t DESC",
    "urgent_escalations": "SELECT cell_id, lot_id, station_id, failure_probability, risk_tier FROM mart_escalation_queue ORDER BY failure_probability DESC LIMIT 20",
}
with sqlite3.connect(db) as c:
    for name, q in queries.items():
        pd.read_sql_query(q, c).to_csv(f"{out}/{name}.csv", index=False)
        print(f"  wrote {out}/{name}.csv")
PY
    exit 0
fi

run_query() {
    local name="$1" sql="$2"
    sqlite3 -header -csv "${DB}" "${sql}" > "${OUT_DIR}/${name}.csv"
    echo "  wrote ${OUT_DIR}/${name}.csv"
}

echo "==> Exporting ad-hoc engineering queries to ${OUT_DIR}"
run_query "lots_highest_risk" \
    "SELECT lot_id, ROUND(AVG(escalation_rate),4) AS escalation_rate FROM mart_factory_quality GROUP BY lot_id ORDER BY escalation_rate DESC LIMIT 10;"
run_query "stations_abnormal" \
    "SELECT station_id, ROUND(AVG(thermal_anomaly_rate),4) AS thermal_anomaly_rate FROM mart_factory_quality GROUP BY station_id ORDER BY thermal_anomaly_rate DESC;"
run_query "urgent_escalations" \
    "SELECT cell_id, lot_id, station_id, failure_probability, risk_tier, top_risk_driver FROM mart_escalation_queue ORDER BY failure_probability DESC LIMIT 20;"

echo "Done."
