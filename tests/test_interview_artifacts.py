"""Checks for panel-interview and ad-hoc investigation artifacts."""
from __future__ import annotations

import re

from src import config


INTERVIEW_ARTIFACTS = [
    "docs/interview/PANEL_INTERVIEW_GUIDE.md",
    "reports/ad_hoc_200_battery_failure_investigation.md",
    "reports/nasa_full_archive_local_run_summary.md",
]


def _read(path: str) -> str:
    return (config.ROOT / path).read_text(encoding="utf-8")


def test_interview_artifacts_exist_and_are_linked_from_readme():
    readme = _read("README.md")
    for rel_path in INTERVIEW_ARTIFACTS:
        assert (config.ROOT / rel_path).is_file(), f"missing {rel_path}"
        assert f"]({rel_path})" in readme, f"README does not link {rel_path}"


def test_readme_local_markdown_links_resolve():
    readme = _read("README.md")
    targets = set(re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme))
    missing = []

    for target in targets:
        if target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        local_target = target.split("#", 1)[0].strip()
        if not local_target:
            continue
        if not (config.ROOT / local_target).exists():
            missing.append(local_target)

    assert not sorted(missing)


def test_panel_interview_guide_has_panel_ready_sections():
    text = _read("docs/interview/PANEL_INTERVIEW_GUIDE.md")
    required = [
        "60-Second Project Summary",
        "How It Maps To The Battery Data Scientist Contractor Role",
        "What Is Real Vs Synthetic",
        "How To Explain It Without Overclaiming",
        "Likely Panel Questions And Strong Answer Bullets",
        "Recommended Files To Skim First",
        "No Apple data, credentials, factory exports, or internal production records are present.",
    ]
    for phrase in required:
        assert phrase in text


def test_ad_hoc_failure_report_covers_battery_engineering_loop():
    text = _read("reports/ad_hoc_200_battery_failure_investigation.md")
    required = [
        "200 batteries/cells were tested",
        "Define The Failure Label",
        "SQL And Grouped Summaries Before ML",
        "Control For Bias And Confounding",
        "Interpretable Baselines Before Complex ML",
        "Class Imbalance And Small Failed Sample Size",
        "Leakage Controls",
        "Validation Splits",
        "Translate Findings Into Engineering Actions",
        "retest",
        "teardown",
        "engineer disposition",
        "station calibration",
        "Lot holdout",
        "Production accuracy would require authorized",
    ]
    for phrase in required:
        assert phrase in text


def test_nasa_full_archive_note_clarifies_default_vs_optional_run():
    text = _read("reports/nasa_full_archive_local_run_summary.md")
    required = [
        "committed/default CI-friendly NASA report uses a small real sample",
        "full official NASA PCoE archive run is optional and local",
        "raw NASA archive is large and should not be committed to Git",
        "34 batteries and 2,750 discharge rows",
        "not to the default committed report",
        "does not prove proprietary factory behavior",
    ]
    for phrase in required:
        assert phrase in text


def test_scorecard_and_packet_include_interview_artifacts():
    scorecard = config.PROJECT_READINESS_SCORECARD.read_text(encoding="utf-8")
    packet = config.HIRING_MANAGER_PACKET.read_text(encoding="utf-8")
    for rel_path in INTERVIEW_ARTIFACTS:
        assert rel_path in scorecard
        assert rel_path in packet
