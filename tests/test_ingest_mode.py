"""Tests for synthetic ingest mode selection."""
from __future__ import annotations

import pandas as pd

from src import config
from src.ingest.load_raw_data import _sources_match_config


def test_synthetic_sources_must_match_active_cell_count(tmp_path, monkeypatch):
    factory = tmp_path / "factory.csv"
    pd.DataFrame({"cell_id": ["CELL-00001", "CELL-00002"]}).to_csv(factory, index=False)

    monkeypatch.setattr(config, "N_CELLS", 2)
    assert _sources_match_config({"factory": factory})

    monkeypatch.setattr(config, "N_CELLS", 45)
    assert not _sources_match_config({"factory": factory})
