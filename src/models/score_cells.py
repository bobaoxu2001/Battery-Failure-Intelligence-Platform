"""Score every cell with the trained models and write predictions.

For each cell we take its latest cycle snapshot and produce:
  * predicted_soh              (SOH regressor on the current snapshot)
  * predicted_remaining_cycles (RUL regressor on the current snapshot)
  * failure_probability        (failure classifier on lifetime features)
  * risk_tier                  (discretised failure probability)
  * top_risk_driver            (most influential adverse feature for that cell)

Predictions are written to ``model_predictions.csv`` and into the warehouse
table ``fact_model_predictions``; the marts are then rebuilt so the escalation
queue reflects the latest scores.

Run as a module::

    python -m src.models.score_cells
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger
from src.warehouse.build_warehouse import build_marts, get_connection

log = get_logger(__name__)

# Human-readable labels + whether a HIGH value is the adverse direction.
DRIVER_META = {
    "final_soh": ("Low state of health", False),
    "soh_current": ("Low state of health", False),
    "capacity_fade_rate": ("Accelerated capacity fade", True),
    "resistance_growth_rate": ("Internal resistance growth", True),
    "peak_temperature_max": ("Peak thermal exposure", True),
    "mean_temperature_max": ("Sustained thermal exposure", True),
    "high_temp_exposure_hours": ("High-temperature field exposure", True),
    "fast_charge_ratio": ("Heavy fast-charge usage", True),
    "avg_depth_of_discharge": ("Deep discharge cycling", True),
    "low_temp_exposure_hours": ("Low-temperature exposure", True),
    "station_anomaly_rate": ("Test-station anomaly signal", True),
    "cycle_count": ("High cumulative cycle count", True),
}


def risk_tier(prob: float) -> str:
    thr = config.RISK_TIER_THRESHOLDS
    if prob >= thr["Critical"]:
        return "Critical"
    if prob >= thr["High"]:
        return "High"
    if prob >= thr["Medium"]:
        return "Medium"
    return "Low"


def _top_drivers(cell_feats: pd.DataFrame, importance: pd.DataFrame) -> list[str]:
    """Per-cell driver = feature with the largest importance-weighted adverse z-score."""
    feats = [f for f in importance["feature"] if f in cell_feats.columns]
    imp = importance.set_index("feature")["importance"].clip(lower=0)
    z = (cell_feats[feats] - cell_feats[feats].mean()) / (cell_feats[feats].std(ddof=0) + 1e-9)

    contrib = pd.DataFrame(index=cell_feats.index)
    for f in feats:
        adverse_high = DRIVER_META.get(f, (f, True))[1]
        signed = z[f] if adverse_high else -z[f]
        contrib[f] = signed.clip(lower=0) * float(imp.get(f, 0.0))

    top_feature = contrib.idxmax(axis=1)
    return [DRIVER_META.get(f, (f, True))[0] for f in top_feature]


def score() -> pd.DataFrame:
    config.ensure_dirs()
    soh_model = C.ModelBundle.load(C.SOH_MODEL_PATH)
    rul_model = C.ModelBundle.load(C.RUL_MODEL_PATH)
    fail_model = C.ModelBundle.load(C.FAILURE_MODEL_PATH)

    cycle_feats = pd.read_csv(config.CYCLE_FEATURES_CSV)
    cell_feats = pd.read_csv(config.CELL_FEATURES_CSV).set_index("cell_id")

    # Latest cycle snapshot per cell for the SOH/RUL regressors.
    latest = cycle_feats.sort_values("cycle_index").groupby("cell_id").tail(1).set_index("cell_id")
    latest = latest.loc[cell_feats.index]

    predicted_soh = soh_model.estimator.predict(latest[soh_model.features].astype(float))
    predicted_rul = rul_model.estimator.predict(latest[rul_model.features].astype(float))
    failure_prob = fail_model.estimator.predict_proba(cell_feats[fail_model.features].astype(float))[:, 1]

    drivers = _top_drivers(cell_feats, fail_model.importance)

    preds = pd.DataFrame({
        "cell_id": cell_feats.index,
        "prediction_date": date.today().isoformat(),
        "predicted_soh": np.round(np.clip(predicted_soh, 0, 1.05), 4),
        "predicted_remaining_cycles": np.round(np.clip(predicted_rul, 0, None), 1),
        "failure_probability": np.round(failure_prob, 4),
        "risk_tier": [risk_tier(p) for p in failure_prob],
        "top_risk_driver": drivers,
    })

    preds.to_csv(config.PREDICTIONS_CSV, index=False)

    # Write to the warehouse and refresh the marts.
    with get_connection() as conn:
        conn.execute("DELETE FROM fact_model_predictions")
        preds.to_sql("fact_model_predictions", conn, if_exists="append", index=False)
        build_marts(conn)
        conn.commit()

    tier_counts = preds["risk_tier"].value_counts().to_dict()
    log.info("Scored %d cells | risk tiers: %s", len(preds), tier_counts)
    log.info("Predictions written to %s and warehouse table fact_model_predictions", config.PREDICTIONS_CSV)
    return preds


if __name__ == "__main__":
    score()
