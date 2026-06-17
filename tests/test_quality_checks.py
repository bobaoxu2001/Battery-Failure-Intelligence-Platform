"""Tests for the warehouse data-quality checks."""
from __future__ import annotations

import sqlite3

import pandas as pd

from src import config
from src.warehouse.quality_checks import parse_checks, run_quality_checks


def test_parse_checks_extracts_named_severity_checks():
    sql = (config.SQL_DIR / "quality_checks.sql").read_text()
    checks = parse_checks(sql)
    assert len(checks) >= 5
    names = {c["name"] for c in checks}
    assert "orphan_cycle_cells" in names
    assert all(c["severity"] in ("HARD", "SOFT") for c in checks)
    assert all(c["sql"].strip().upper().startswith("SELECT") for c in checks)


def test_all_hard_checks_pass_on_built_warehouse():
    results = run_quality_checks(raise_on_fail=False)
    hard = results[results["severity"] == "HARD"]
    assert hard["passed"].all(), f"hard QC failed: {hard[~hard['passed']]['name'].tolist()}"


def test_quality_checks_return_expected_schema():
    results = run_quality_checks(raise_on_fail=False)
    assert set(results.columns) == {"name", "severity", "offending", "passed"}
    assert (results["offending"] >= 0).all()


def test_warehouse_has_all_expected_tables():
    expected = {
        "dim_cell", "dim_lot", "dim_station", "dim_test_condition",
        "fact_cycle_measurements", "fact_usage_profile", "fact_failure_events",
        "fact_model_predictions", "stg_cell_features",
        "mart_cell_health_summary", "mart_factory_quality", "mart_escalation_queue",
    }
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        tables = set(pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'", conn)["name"])
    assert expected.issubset(tables), f"missing tables: {expected - tables}"


def test_marts_are_non_empty():
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        health = pd.read_sql_query("SELECT COUNT(*) n FROM mart_cell_health_summary", conn)
        factory = pd.read_sql_query("SELECT COUNT(*) n FROM mart_factory_quality", conn)
    assert int(health["n"][0]) > 0
    assert int(factory["n"][0]) > 0
