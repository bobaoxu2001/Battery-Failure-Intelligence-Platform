"""Shared pytest fixtures.

Ensures the pipeline artifacts the tests assert on actually exist. If a fresh
clone runs ``pytest`` before ``run_daily_pipeline.sh``, this builds the minimal
set of artifacts (data -> features -> warehouse -> models -> predictions) once
per test session so the suite is self-contained.
"""
from __future__ import annotations

import pytest

from src import config


def _build_if_missing() -> None:
    need = [
        config.CYCLE_FEATURES_CSV,
        config.CELL_FEATURES_CSV,
        config.WAREHOUSE_DB,
        config.PREDICTIONS_CSV,
        config.REPORTS_DIR / "escalation_report_sample.csv",
    ]
    models = [
        config.MODELS_DIR / "soh_model.joblib",
        config.MODELS_DIR / "rul_model.joblib",
        config.MODELS_DIR / "failure_model.joblib",
    ]
    if all(p.exists() for p in need + models):
        return

    from src.ingest.load_raw_data import load
    from src.features.build_features import build as build_features
    from src.warehouse.build_warehouse import build as build_warehouse
    from src.models.train_soh_model import train as train_soh
    from src.models.train_rul_model import train as train_rul
    from src.models.train_failure_classifier import train as train_failure
    from src.models.score_cells import score
    from src.reporting.generate_escalation_report import generate as gen_escalation

    load()
    build_features()
    build_warehouse()
    if not all(p.exists() for p in models):
        train_soh()
        train_rul()
        train_failure()
    score()
    gen_escalation()


@pytest.fixture(scope="session", autouse=True)
def pipeline_artifacts():
    """Guarantee processed data, warehouse, models and reports exist."""
    _build_if_missing()
    yield
