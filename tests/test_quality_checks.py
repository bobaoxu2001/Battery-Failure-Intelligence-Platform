"""Tests for the warehouse data-quality checks."""
from __future__ import annotations

import os
import sqlite3

import pandas as pd

from src import config
from src.warehouse.build_warehouse import _features_need_rebuild
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


def test_staged_features_align_with_cell_dimension():
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        missing_features = pd.read_sql_query(
            """
            SELECT COUNT(*) n
            FROM dim_cell c
            LEFT JOIN stg_cell_features f ON f.cell_id = c.cell_id
            WHERE f.cell_id IS NULL
            """,
            conn,
        )
        orphan_features = pd.read_sql_query(
            """
            SELECT COUNT(*) n
            FROM stg_cell_features f
            LEFT JOIN dim_cell c ON c.cell_id = f.cell_id
            WHERE c.cell_id IS NULL
            """,
            conn,
        )
    assert int(missing_features["n"][0]) == 0
    assert int(orphan_features["n"][0]) == 0


def test_feature_freshness_detects_stale_artifacts(tmp_path, monkeypatch):
    paths = {
        "FACTORY_CSV": tmp_path / "factory.csv",
        "CYCLES_CSV": tmp_path / "cycles.csv",
        "USAGE_CSV": tmp_path / "usage.csv",
        "FAILURES_CSV": tmp_path / "failure_events.csv",
        "CYCLE_FEATURES_CSV": tmp_path / "cycle_features.csv",
        "CELL_FEATURES_CSV": tmp_path / "cell_features.csv",
    }
    for attr, path in paths.items():
        path.write_text("placeholder\n", encoding="utf-8")
        monkeypatch.setattr(config, attr, path)

    for attr in ("FACTORY_CSV", "CYCLES_CSV", "USAGE_CSV", "FAILURES_CSV"):
        os.utime(paths[attr], (2000, 2000))
    for attr in ("CYCLE_FEATURES_CSV", "CELL_FEATURES_CSV"):
        os.utime(paths[attr], (1000, 1000))
    assert _features_need_rebuild()

    for attr in ("CYCLE_FEATURES_CSV", "CELL_FEATURES_CSV"):
        os.utime(paths[attr], (3000, 3000))
    assert not _features_need_rebuild()
