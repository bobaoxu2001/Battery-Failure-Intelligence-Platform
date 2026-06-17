"""Train the State-of-Health (SOH) regression model.

Target:  ``soh_current`` = discharge_capacity / initial_capacity.
Approach: a Linear Regression baseline vs. a RandomForest / gradient-boosting
model; the better RMSE on a *cell-grouped* hold-out set is kept as the artifact.
SOH is estimated from resistance + thermal + usage signals (capacity-derived
columns are excluded to avoid leaking the target).

Run as a module::

    python -m src.models.train_soh_model
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def train() -> C.ModelBundle:
    config.ensure_dirs()
    frame = pd.read_csv(config.CYCLE_FEATURES_CSV)
    X_tr, X_te, y_tr, y_te = C.grouped_split(frame, C.SOH_FEATURES, "soh_current", "cell_id")

    candidates = {
        "LinearRegression": C.linear_baseline(),
        C.boosted_regressor()[0]: C.boosted_regressor()[1],
        "RandomForest": C.random_forest_regressor(),
    }

    best = None
    for name, est in candidates.items():
        est.fit(X_tr, y_tr)
        metrics = C.regression_metrics(y_te, est.predict(X_te))
        log.info("SOH %-16s MAE=%.4f RMSE=%.4f R2=%.3f", name, metrics["MAE"], metrics["RMSE"], metrics["R2"])
        if best is None or metrics["RMSE"] < best[2]["RMSE"]:
            best = (name, est, metrics)

    name, est, metrics = best
    importance = C.importance_table(est, X_te, y_te, C.SOH_FEATURES)
    bundle = C.ModelBundle(
        name="soh_regressor", target="soh_current", features=C.SOH_FEATURES,
        estimator=est, metrics=metrics, importance=importance, algorithm=name,
    )
    bundle.save(C.SOH_MODEL_PATH)
    log.info("Saved SOH model (%s) -> %s | RMSE=%.4f R2=%.3f", name, C.SOH_MODEL_PATH, metrics["RMSE"], metrics["R2"])
    return bundle


if __name__ == "__main__":
    train()
