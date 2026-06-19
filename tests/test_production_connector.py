"""Tests for the authorized-only production connector scaffold."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.ingest.production_connector import (
    EXPECTED_SCHEMA,
    ProductionConnectorConfigError,
    ProductionDataConfig,
    load_factory_cell_tests,
    render_schema_contract,
)


ROOT = Path(__file__).resolve().parents[1]
MOCK_DIR = ROOT / "data" / "mock_production"


def test_production_connector_refuses_missing_credentials(monkeypatch):
    for key in (
        "BFI_PROD_DB_URI",
        "BFI_PROD_DB_SCHEMA",
        "BFI_PROD_READ_ONLY",
        "BFI_PROD_SAMPLE_LIMIT",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ProductionConnectorConfigError, match="Missing: BFI_PROD_DB_URI"):
        ProductionDataConfig.from_env(require_credentials=True)


def test_dry_run_validates_config_without_real_data(monkeypatch):
    env = os.environ.copy()
    env.update(
        {
            "BFI_PROD_DB_URI": "mock+readonly://authorized-placeholder",
            "BFI_PROD_DB_SCHEMA": "battery_quality",
            "BFI_PROD_READ_ONLY": "true",
            "BFI_PROD_SAMPLE_LIMIT": "25",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "src.ingest.production_connector", "--dry-run"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "No connection was opened" in result.stdout
    assert "battery_quality" in result.stdout


def test_schema_contract_only_mode_works_without_credentials(monkeypatch):
    monkeypatch.delenv("BFI_PROD_DB_URI", raising=False)
    result = subprocess.run(
        [sys.executable, "-m", "src.ingest.production_connector", "--schema-contract-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "factory_cell_tests" in result.stdout
    assert "cycle_measurements" in result.stdout


def test_render_schema_contract_lists_expected_tables():
    text = render_schema_contract()
    for table in EXPECTED_SCHEMA:
        assert table in text


def test_placeholder_loaders_do_not_connect(monkeypatch):
    monkeypatch.setenv("BFI_PROD_DB_URI", "mock+readonly://authorized-placeholder")
    monkeypatch.setenv("BFI_PROD_DB_SCHEMA", "battery_quality")
    monkeypatch.setenv("BFI_PROD_READ_ONLY", "true")
    monkeypatch.setenv("BFI_PROD_SAMPLE_LIMIT", "10")

    with pytest.raises(NotImplementedError, match="never connects to private systems"):
        load_factory_cell_tests()


def test_mock_production_fixtures_load_successfully():
    expected = {
        "factory_cell_tests_sample.csv": {"cell_test_id", "cell_id", "lot_id", "station_id"},
        "cycle_measurements_sample.csv": {"cell_id", "cycle_index", "discharge_capacity_ah"},
        "usage_telemetry_sample.csv": {"usage_window_id", "cell_id", "fast_charge_ratio"},
        "failure_events_sample.csv": {"failure_event_id", "cell_id", "escalation_required"},
        "station_calibration_logs_sample.csv": {"calibration_event_id", "station_id", "calibration_status"},
    }
    for filename, required_columns in expected.items():
        frame = pd.read_csv(MOCK_DIR / filename)
        assert len(frame) > 0
        assert required_columns.issubset(frame.columns)

    readme = (MOCK_DIR / "README.md").read_text(encoding="utf-8")
    assert "not Apple data" in readme
    assert "not production data" in readme


def test_no_real_credentials_are_present_in_repo_files():
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    secret_patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
        re.compile(r"(?i)(password|secret|token)\s*=\s*[^\\s#]+"),
        re.compile(r"BFI_PROD_DB_URI=(?!$)(?!\"?mock\+readonly://placeholder)\S+"),
    ]
    for rel_path in tracked:
        path = ROOT / rel_path
        if path.suffix in {".png", ".joblib", ".db", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in secret_patterns:
            assert not pattern.search(text), f"possible credential in {rel_path}"


def test_raw_production_paths_are_gitignored():
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            ".env",
            "data/production/raw_cells.csv",
            "data/private/export.csv",
            "data/prod_exports/query_result.csv",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    ignored = set(result.stdout.splitlines())
    assert ".env" in ignored
    assert "data/production/raw_cells.csv" in ignored
    assert "data/private/export.csv" in ignored
    assert "data/prod_exports/query_result.csv" in ignored
