"""Import Oxford Battery Degradation Dataset 1 for second-source validation.

Source: Oxford University Research Archive record
``Oxford Battery Degradation Dataset 1``. The full raw ``.mat`` file is large
and intentionally gitignored; this module prefers the local official archive
when present, then falls back to a committed normalized sample.

Run as a module::

    python -m src.ingest.import_oxford_battery_data
    python -m src.ingest.import_oxford_battery_data --source full
    python -m src.ingest.import_oxford_battery_data --source example
"""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd

from src import config
from src.ingest.oxford_mat_parser import (
    OXFORD_DATASET_NAME,
    OXFORD_DOI,
    OXFORD_OFFICIAL_URL,
    battery_rollup,
    parse_oxford_mat,
)
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def build_oxford_cycle_summary(source: str = "auto") -> pd.DataFrame:
    config.ensure_dirs()
    summary: pd.DataFrame | None = None
    source_mode = ""

    if source in ("auto", "full") and config.OXFORD_FULL_MAT.exists():
        summary = parse_oxford_mat(config.OXFORD_FULL_MAT)
        source_mode = "official full Oxford .mat archive"
        if source == "full" and summary.empty:
            raise ValueError(f"No rows parsed from {config.OXFORD_FULL_MAT}")

    if summary is None and source in ("auto", "example") and config.OXFORD_EXAMPLE_MAT.exists():
        summary = parse_oxford_mat(config.OXFORD_EXAMPLE_MAT)
        source_mode = "official Oxford example .mat"

    if summary is None:
        if not config.OXFORD_REAL_SAMPLE_CSV.exists():
            raise FileNotFoundError(
                "No Oxford source found. Place official .mat files under "
                "data/raw/public/oxford/ or keep the bundled sample CSV."
            )
        summary = pd.read_csv(config.OXFORD_REAL_SAMPLE_CSV)
        source_mode = "bundled normalized Oxford sample"

    summary.attrs["source_mode"] = source_mode
    summary.to_csv(config.OXFORD_REAL_CYCLE_SUMMARY_CSV, index=False)
    log.info("Wrote Oxford real cycle summary %s (%d rows)", config.OXFORD_REAL_CYCLE_SUMMARY_CSV, len(summary))
    return summary


def build_report(summary: pd.DataFrame | None = None) -> str:
    config.ensure_dirs()
    if summary is None:
        summary = pd.read_csv(config.OXFORD_REAL_CYCLE_SUMMARY_CSV)
    source_mode = summary.attrs.get("source_mode", "normalized CSV")
    rollup = battery_rollup(summary)
    lines = [
        "# Oxford Real Battery Data Validation",
        "",
        f"_Generated: {date.today().isoformat()}._",
        "",
        "This report adds a second real public battery-aging source beyond NASA. It is used as cross-dataset parser and degradation-coverage evidence, not as production accuracy proof.",
        "",
        f"- Source dataset: {OXFORD_DATASET_NAME}",
        f"- Official upstream: {OXFORD_OFFICIAL_URL}",
        f"- DOI: {OXFORD_DOI}",
        "- Dataset description: long-term cycling of 8 Kokam 740 mAh lithium-ion pouch cells",
        f"- Run source mode: {source_mode}",
        f"- Parsed cells: {rollup['cell_id'].nunique()}",
        f"- Parsed cycle snapshots: {len(summary)}",
        "",
        "## Cell-Level Degradation Summary",
        "",
        "| Cell | Snapshots | Cycle range | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in rollup.iterrows():
        first_below = "" if pd.isna(row["first_cycle_below_80pct_soh"]) else int(row["first_cycle_below_80pct_soh"])
        lines.append(
            f"| {row['cell_id']} | {int(row['snapshots'])} | {int(row['first_cycle_index'])}-{int(row['last_cycle_index'])} | "
            f"{row['initial_capacity_ah']:.3f} | {row['final_capacity_ah']:.3f} | {row['capacity_loss_pct']:.1%} | "
            f"{first_below} | {row['max_discharge_temp_c']:.1f} | {row['capacity_cycle_corr']:.3f} |"
        )
    lines += [
        "",
        "## Boundary",
        "",
        "Oxford validates a different lab, cell form factor, and test structure than NASA. The adapter intentionally normalizes only shared cycle-level degradation fields so the project can compare public sources without pretending they share a factory schema.",
    ]
    md = "\n".join(lines) + "\n"
    config.OXFORD_REAL_DATA_REPORT.write_text(md, encoding="utf-8")
    log.info("Wrote Oxford validation report %s", config.OXFORD_REAL_DATA_REPORT)
    return md


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Oxford public battery aging data")
    parser.add_argument("--source", choices=["auto", "full", "example", "sample"], default="auto")
    args = parser.parse_args()
    if args.source == "sample":
        summary = pd.read_csv(config.OXFORD_REAL_SAMPLE_CSV)
        summary.attrs["source_mode"] = "bundled normalized Oxford sample"
        summary.to_csv(config.OXFORD_REAL_CYCLE_SUMMARY_CSV, index=False)
    else:
        summary = build_oxford_cycle_summary(args.source)
    build_report(summary)


if __name__ == "__main__":
    main()
