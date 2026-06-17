"""Generate Tableau-ready CSV extracts from the warehouse marts.

Tableau Desktop is *not* required to run this project. This step exports flat,
denormalised CSV extracts (one per dashboard page) into
``dashboards/tableau_extracts/`` so they can be dropped straight into Tableau,
Excel, or any BI tool. Optionally renders static matplotlib mock dashboards.

Run as a module::

    python -m src.reporting.generate_tableau_extracts
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from src import config
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

# Extract name -> SQL pulling a flat, dashboard-ready table from the warehouse.
EXTRACTS = {
    "executive_battery_health": """
        SELECT cell_id, lot_id, station_id, usage_profile, cycle_count,
               last_soh, predicted_soh, predicted_remaining_cycles,
               failure_probability, risk_tier, top_risk_driver
        FROM mart_cell_health_summary
    """,
    "factory_lot_quality": """
        SELECT lot_id, station_id, num_cells, avg_final_soh,
               avg_capacity_fade_rate, avg_resistance_growth_rate,
               escalation_rate, early_degradation_rate,
               thermal_anomaly_rate, impedance_spike_rate
        FROM mart_factory_quality
    """,
    "engineering_root_cause": """
        SELECT s.usage_profile, s.top_risk_driver, COUNT(*) AS cells,
               ROUND(AVG(s.capacity_fade_rate), 6) AS avg_capacity_fade_rate,
               ROUND(AVG(s.resistance_growth_rate), 6) AS avg_resistance_growth_rate,
               ROUND(AVG(s.failure_probability), 4) AS avg_failure_probability
        FROM mart_cell_health_summary s
        GROUP BY s.usage_profile, s.top_risk_driver
    """,
    "escalation_queue": "SELECT * FROM mart_escalation_queue",
}


def generate() -> dict[str, pd.DataFrame]:
    config.ensure_dirs()
    extracts: dict[str, pd.DataFrame] = {}
    with sqlite3.connect(config.WAREHOUSE_DB) as conn:
        for name, sql in EXTRACTS.items():
            df = pd.read_sql_query(sql, conn)
            path = config.TABLEAU_EXTRACTS_DIR / f"{name}.csv"
            df.to_csv(path, index=False)
            extracts[name] = df
            log.info("Wrote Tableau extract %-26s %d rows -> %s", name, len(df), path.name)

    _render_mock_dashboards(extracts)
    return extracts


def _render_mock_dashboards(extracts: dict[str, pd.DataFrame]) -> None:
    """Render static PNG mock dashboards (best-effort; skipped if matplotlib absent)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        log.warning("matplotlib unavailable - skipping static mock dashboards")
        return

    health = extracts["executive_battery_health"]
    lot = extracts["factory_lot_quality"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    fig.suptitle("Battery Failure Intelligence - Executive Overview (synthetic data)", fontweight="bold")

    tier_order = ["Low", "Medium", "High", "Critical"]
    counts = health["risk_tier"].value_counts().reindex(tier_order).fillna(0)
    colors = ["#2e7d32", "#f9a825", "#ef6c00", "#c62828"]
    axes[0].bar(tier_order, counts.values, color=colors)
    axes[0].set_title("Fleet by risk tier")
    axes[0].set_ylabel("Cells")
    for i, v in enumerate(counts.values):
        axes[0].text(i, v + 0.5, str(int(v)), ha="center")

    axes[1].scatter(health["predicted_remaining_cycles"], health["predicted_soh"],
                    c=health["failure_probability"], cmap="RdYlGn_r", s=28, edgecolor="k", linewidth=0.3)
    axes[1].axhline(config.SOH_EOL_THRESHOLD, ls="--", color="grey", lw=1)
    axes[1].set_title("Predicted SOH vs remaining cycles")
    axes[1].set_xlabel("Predicted remaining cycles")
    axes[1].set_ylabel("Predicted SOH")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(config.MOCKUPS_DIR / "executive_overview.png", dpi=110)
    plt.close(fig)

    # Factory lot-quality heat-style bar of escalation rate by lot.
    lot_roll = lot.groupby("lot_id")["escalation_rate"].mean().sort_values(ascending=False)
    fig2, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(lot_roll.index, lot_roll.values, color="#c62828")
    ax.set_title("Factory lot quality - escalation rate by lot (synthetic)", fontweight="bold")
    ax.set_ylabel("Escalation rate")
    ax.set_xlabel("Lot")
    ax.tick_params(axis="x", rotation=45)
    fig2.tight_layout()
    fig2.savefig(config.MOCKUPS_DIR / "factory_lot_quality.png", dpi=110)
    plt.close(fig2)

    log.info("Rendered static mock dashboards -> %s", config.MOCKUPS_DIR)


if __name__ == "__main__":
    generate()
