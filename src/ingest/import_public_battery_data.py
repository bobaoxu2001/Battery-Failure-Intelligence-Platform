"""Import public real battery data for external validation.

The main platform uses synthetic data so every pipeline run is deterministic and
fast. This module adds a real-data validation layer using NASA PCoE battery
aging data, with three sources tried in order of authority:

1. **Official ``.mat`` archive** (``data/raw/5. Battery Data Set/``) parsed
   directly via :mod:`src.ingest.nasa_mat_parser` — the authoritative source.
2. **Processed-CSV mirror** (a small third-party convenience mirror) for quick
   demos when the official archive is not on disk.
3. **Committed bundled sample** (``data/public_samples/``) so CI and fresh
   clones still produce a real-data report with no downloads.

Run as a module::

    python -m src.ingest.import_public_battery_data                 # auto source
    python -m src.ingest.import_public_battery_data --source archive
    python -m src.ingest.import_public_battery_data --download       # mirror CSVs
    python -m src.ingest.import_public_battery_data --battery-id B0005 --battery-id B0018

If network access is slow, place files named ``B0005_processed.csv`` etc. under
``data/raw/public/nasa_processed_csv/`` and run the module without ``--download``.
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

NASA_PCOE_DATASET_URL = "https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip"
PROCESSED_CSV_URLS = {
    "B0005": "https://raw.githubusercontent.com/natskiu/Nasa-Battery/main/processed_csv/B0005_processed.csv",
    "B0006": "https://raw.githubusercontent.com/natskiu/Nasa-Battery/main/processed_csv/B0006_processed.csv",
    "B0007": "https://raw.githubusercontent.com/natskiu/Nasa-Battery/main/processed_csv/B0007_processed.csv",
    "B0018": "https://raw.githubusercontent.com/natskiu/Nasa-Battery/main/processed_csv/B0018_processed.csv",
}


@dataclass(frozen=True)
class RealDataSource:
    name: str = "NASA PCoE Battery Aging Data"
    official_url: str = NASA_PCOE_DATASET_URL
    processed_mirror: str = "https://github.com/natskiu/Nasa-Battery"
    note: str = (
        "Public lithium-ion battery aging data from NASA PCoE; processed CSV mirror "
        "is used only as a lightweight adapter input."
    )


def _run_curl(url: str, out_path: Path, timeout_seconds: int = 120) -> bool:
    """Download one file with curl; return False on network/HTTP failure."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl",
        "--fail",
        "--location",
        "--connect-timeout",
        "20",
        "--max-time",
        str(timeout_seconds),
        "--silent",
        "--show-error",
        url,
        "-o",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True)
        return out_path.exists() and out_path.stat().st_size > 0
    except (OSError, subprocess.CalledProcessError) as exc:
        log.warning("Download failed for %s -> %s (%s)", url, out_path, exc)
        if out_path.exists() and out_path.stat().st_size == 0:
            out_path.unlink()
        return False


def download_processed_csvs(battery_ids: list[str] | None = None) -> list[Path]:
    """Download lightweight processed NASA CSV files when network allows."""
    config.ensure_dirs()
    battery_ids = battery_ids or list(PROCESSED_CSV_URLS)
    paths: list[Path] = []
    for battery_id in battery_ids:
        url = PROCESSED_CSV_URLS.get(battery_id)
        if not url:
            log.warning("No processed CSV URL configured for %s", battery_id)
            continue
        out = config.NASA_PROCESSED_CSV_DIR / f"{battery_id}_processed.csv"
        if out.exists() and out.stat().st_size > 0:
            paths.append(out)
            continue
        if _run_curl(url, out):
            paths.append(out)
    return paths


def available_processed_csvs(battery_ids: list[str] | None = None) -> list[Path]:
    battery_ids = battery_ids or list(PROCESSED_CSV_URLS)
    paths = [config.NASA_PROCESSED_CSV_DIR / f"{battery_id}_processed.csv" for battery_id in battery_ids]
    return [path for path in paths if path.exists() and path.stat().st_size > 0]


def _normalise_processed_csv(path: Path) -> pd.DataFrame:
    battery_id = path.stem.replace("_processed", "")
    raw = pd.read_csv(path)
    if "capacity" not in raw.columns or "remaining_cycles" not in raw.columns:
        raise ValueError(f"{path} is missing required processed NASA columns")
    raw = raw.rename(columns={raw.columns[0]: "cycle_index"}).copy()
    raw["cycle_index"] = pd.to_numeric(raw["cycle_index"], errors="coerce").astype("Int64")
    raw["capacity_ah"] = pd.to_numeric(raw["capacity"], errors="coerce")
    raw["remaining_cycles"] = pd.to_numeric(raw["remaining_cycles"], errors="coerce")
    raw["max_discharge_temp_c"] = pd.to_numeric(raw.get("max_temp_D"), errors="coerce")
    raw["max_charge_temp_c"] = pd.to_numeric(raw.get("max_temp_C"), errors="coerce")
    raw["discharge_temp_slope"] = pd.to_numeric(raw.get("slope_temp_D"), errors="coerce")
    raw["voltage_slope"] = pd.to_numeric(raw.get("slope_voltage_measured_D"), errors="coerce")

    first_capacity = float(raw["capacity_ah"].dropna().iloc[0])
    raw["soh"] = raw["capacity_ah"] / first_capacity
    raw["battery_id"] = battery_id
    raw["source_dataset"] = "NASA PCoE Battery Aging Data"
    raw["source_adapter"] = "processed_csv_mirror"
    cols = [
        "source_dataset",
        "source_adapter",
        "battery_id",
        "cycle_index",
        "capacity_ah",
        "soh",
        "remaining_cycles",
        "max_discharge_temp_c",
        "max_charge_temp_c",
        "discharge_temp_slope",
        "voltage_slope",
    ]
    return raw[cols].dropna(subset=["cycle_index", "capacity_ah"]).reset_index(drop=True)


def _summary_from_official_archive(battery_ids: list[str] | None) -> pd.DataFrame | None:
    """Parse the official NASA ``.mat`` archive if it is present on disk."""
    from src.ingest.nasa_mat_parser import build_zip_index, parse_batteries

    if not build_zip_index():
        return None
    summary = parse_batteries(battery_ids)
    log.info("Used official NASA .mat archive (%d rows, %d batteries)",
             len(summary), summary["battery_id"].nunique())
    return summary


def _summary_from_mirror(download: bool, battery_ids: list[str] | None) -> pd.DataFrame | None:
    """Parse the processed-CSV mirror if files are available (optionally downloaded)."""
    if download:
        download_processed_csvs(battery_ids)
    paths = available_processed_csvs(battery_ids)
    if not paths:
        return None
    summary = pd.concat([_normalise_processed_csv(path) for path in paths], ignore_index=True)
    log.info("Used processed-CSV mirror (%d rows, %d batteries)",
             len(summary), summary["battery_id"].nunique())
    return summary


def _summary_from_bundled_sample() -> pd.DataFrame | None:
    if not config.NASA_REAL_SAMPLE_CSV.exists():
        return None
    sample = pd.read_csv(config.NASA_REAL_SAMPLE_CSV)
    log.info("Used bundled NASA real-data sample %s (%d rows)",
             config.NASA_REAL_SAMPLE_CSV, len(sample))
    return sample


def build_real_cycle_summary(
    download: bool = False,
    battery_ids: list[str] | None = None,
    source: str = "auto",
) -> pd.DataFrame:
    """Build a normalized real-data cycle summary from the best available source.

    ``source`` is one of ``auto`` (archive -> mirror -> bundled sample),
    ``archive``, ``mirror`` or ``sample``.
    """
    config.ensure_dirs()
    summary: pd.DataFrame | None = None

    if source in ("auto", "archive"):
        summary = _summary_from_official_archive(battery_ids)
        if summary is None and source == "archive":
            raise FileNotFoundError(
                f"Official NASA archive not found under {config.NASA_OFFICIAL_ARCHIVE_DIR}."
            )

    if summary is None and source in ("auto", "mirror"):
        summary = _summary_from_mirror(download, battery_ids)
        if summary is None and source == "mirror":
            raise FileNotFoundError(
                "No NASA processed CSV files found. Run with --download or place "
                "`B0005_processed.csv` files under data/raw/public/nasa_processed_csv/."
            )

    if summary is None:  # auto fallback, or source == "sample"
        summary = _summary_from_bundled_sample()

    if summary is None:
        raise FileNotFoundError(
            "No real-data source available: official archive, processed-CSV mirror "
            "and bundled sample are all missing."
        )

    summary.to_csv(config.NASA_REAL_CYCLE_SUMMARY_CSV, index=False)
    log.info("Wrote real NASA cycle summary %s (%d rows, %d batteries)",
             config.NASA_REAL_CYCLE_SUMMARY_CSV, len(summary), summary["battery_id"].nunique())
    return summary


def _battery_rollup(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for battery_id, group in summary.groupby("battery_id"):
        group = group.sort_values("cycle_index")
        initial = float(group["capacity_ah"].iloc[0])
        final = float(group["capacity_ah"].iloc[-1])
        corr = float(np.corrcoef(group["cycle_index"], group["capacity_ah"])[0, 1]) if len(group) > 2 else np.nan
        below_80 = group[group["soh"] < config.SOH_EOL_THRESHOLD]
        rows.append(
            {
                "battery_id": battery_id,
                "cycles": int(group["cycle_index"].max() + 1),
                "initial_capacity_ah": initial,
                "final_capacity_ah": final,
                "capacity_loss_pct": (initial - final) / initial,
                "first_cycle_below_80pct_soh": (
                    int(below_80["cycle_index"].iloc[0]) if not below_80.empty else None
                ),
                "capacity_cycle_corr": corr,
                "max_discharge_temp_c": float(group["max_discharge_temp_c"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values("battery_id").reset_index(drop=True)


def build_report(summary: pd.DataFrame | None = None) -> str:
    """Write a Markdown report proving real public battery data was parsed."""
    config.ensure_dirs()
    source = RealDataSource()
    if summary is None:
        summary = pd.read_csv(config.NASA_REAL_CYCLE_SUMMARY_CSV)
    rollup = _battery_rollup(summary)
    adapters = sorted(summary["source_adapter"].dropna().unique()) if "source_adapter" in summary else []
    adapter_label = {
        "official_mat_archive": "official NASA .mat archive (authoritative)",
        "processed_csv_mirror": "processed-CSV mirror (third-party convenience)",
    }
    adapter_text = ", ".join(adapter_label.get(a, a) for a in adapters) or "bundled sample"
    lines = [
        "# Real Public Battery Data Validation",
        "",
        f"_Generated: {date.today().isoformat()}._",
        "",
        "This report uses **real public lithium-ion battery aging data** for validation.",
        "It does not use any confidential or proprietary data.",
        "",
        f"- Source dataset: {source.name}",
        f"- Official upstream: {source.official_url}",
        f"- Adapter used: {adapter_text}",
        f"- Processed-CSV mirror (fallback): {source.processed_mirror}",
        f"- Parsed batteries: {', '.join(rollup['battery_id'].tolist())}",
        f"- Parsed cycle rows: {len(summary)}",
        "",
        "## Battery-Level Degradation Summary",
        "",
        "| Battery | Cycles | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in rollup.iterrows():
        first_below = "" if pd.isna(row["first_cycle_below_80pct_soh"]) else int(row["first_cycle_below_80pct_soh"])
        lines.append(
            f"| {row['battery_id']} | {int(row['cycles'])} | {row['initial_capacity_ah']:.3f} | "
            f"{row['final_capacity_ah']:.3f} | {row['capacity_loss_pct']:.1%} | {first_below} | "
            f"{row['max_discharge_temp_c']:.1f} | {row['capacity_cycle_corr']:.3f} |"
        )
    lines += [
        "",
        "## How this is used",
        "The main warehouse/model pipeline remains synthetic and fully reproducible.",
        "This real-data layer is an external sanity check: it verifies that the project can ingest public battery aging data and recover physically sensible degradation trends.",
    ]
    md = "\n".join(lines) + "\n"
    config.REAL_DATA_VALIDATION_REPORT.write_text(md, encoding="utf-8")
    log.info("Wrote real-data validation report %s", config.REAL_DATA_VALIDATION_REPORT)
    return md


def main() -> None:
    parser = argparse.ArgumentParser(description="Import public NASA battery aging data")
    parser.add_argument("--download", action="store_true", help="download processed NASA CSVs before parsing")
    parser.add_argument("--battery-id", action="append", dest="battery_ids", help="battery id to parse, e.g. B0005")
    parser.add_argument("--source", choices=["auto", "archive", "mirror", "sample"], default="auto",
                        help="real-data source: auto (default), official archive, processed-CSV mirror, or bundled sample")
    args = parser.parse_args()
    summary = build_real_cycle_summary(
        download=args.download, battery_ids=args.battery_ids, source=args.source
    )
    build_report(summary)


if __name__ == "__main__":
    main()
