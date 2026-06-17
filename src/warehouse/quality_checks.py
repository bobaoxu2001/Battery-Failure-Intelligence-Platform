"""Run SQL data-quality checks against the warehouse.

The checks live in ``sql/quality_checks.sql``. Each is annotated with a name and
a severity (HARD or SOFT) in a ``-- name: <name> (HARD|SOFT)`` comment. A HARD
failure (offending rows > 0) raises and fails the pipeline; a SOFT failure is
logged as a warning. Returns a results DataFrame for tests/reporting.

Run as a module::

    python -m src.warehouse.quality_checks
"""
from __future__ import annotations

import re
import sqlite3

import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

_CHECK_RE = re.compile(r"--\s*name:\s*(?P<name>\w+)\s*\((?P<severity>HARD|SOFT)\)", re.IGNORECASE)


def parse_checks(sql_text: str) -> list[dict]:
    """Split the quality-check file into individual named/severity-tagged checks."""
    checks: list[dict] = []
    current = None
    buffer: list[str] = []
    for line in sql_text.splitlines():
        match = _CHECK_RE.search(line)
        if match:
            if current:
                current["sql"] = "\n".join(buffer).strip()
                checks.append(current)
            current = {"name": match.group("name"), "severity": match.group("severity").upper()}
            buffer = []
        elif current is not None and not line.strip().startswith("--"):
            buffer.append(line)
    if current:
        current["sql"] = "\n".join(buffer).strip()
        checks.append(current)
    return [c for c in checks if c["sql"]]


def run_quality_checks(raise_on_fail: bool = True) -> pd.DataFrame:
    """Execute all checks; return a DataFrame of (name, severity, offending, passed)."""
    sql_text = (config.SQL_DIR / "quality_checks.sql").read_text(encoding="utf-8")
    checks = parse_checks(sql_text)

    rows = []
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        for check in checks:
            offending = int(pd.read_sql_query(check["sql"], conn).iloc[0, 0])
            passed = offending == 0
            rows.append({**{k: check[k] for k in ("name", "severity")},
                         "offending": offending, "passed": passed})
            level = log.info if passed else (log.error if check["severity"] == "HARD" else log.warning)
            level("QC %-30s %-4s offending=%d %s",
                  check["name"], check["severity"], offending, "OK" if passed else "FAIL")

    results = pd.DataFrame(rows)
    hard_failures = results[(~results["passed"]) & (results["severity"] == "HARD")]
    if raise_on_fail and not hard_failures.empty:
        raise RuntimeError(f"Hard data-quality checks failed: {list(hard_failures['name'])}")
    return results


if __name__ == "__main__":
    run_quality_checks()
