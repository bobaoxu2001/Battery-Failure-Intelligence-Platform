"""Train the Remaining-Useful-Life (RUL) regression model.

Target:  ``remaining_cycles`` until SOH crosses the 80% end-of-life threshold.
Approach: RandomForest vs. gradient-boosting regressor on a cell-grouped split;
the lower-RMSE model is persisted. RUL legitimately uses current SOH and the
recent degradation trend as inputs.

Run as a module::

    python -m src.models.train_rul_model
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
    X_tr, X_te, y_tr, y_te = C.grouped_split(frame, C.RUL_FEATURES, "remaining_cycles", "cell_id")

    boost_name, boost_est = C.boosted_regressor()
    candidates = {
        "RandomForest": C.random_forest_regressor(),
        boost_name: boost_est,
    }

    best = None
    for name, est in candidates.items():
        est.fit(X_tr, y_tr)
        metrics = C.regression_metrics(y_te, est.predict(X_te))
        log.info("RUL %-16s MAE=%.1f RMSE=%.1f R2=%.3f", name, metrics["MAE"], metrics["RMSE"], metrics["R2"])
        if best is None or metrics["RMSE"] < best[2]["RMSE"]:
            best = (name, est, metrics)

    name, est, metrics = best
    importance = C.importance_table(est, X_te, y_te, C.RUL_FEATURES)
    bundle = C.ModelBundle(
        name="rul_regressor", target="remaining_cycles", features=C.RUL_FEATURES,
        estimator=est, metrics=metrics, importance=importance, algorithm=name,
    )
    bundle.save(C.RUL_MODEL_PATH)
    log.info("Saved RUL model (%s) -> %s | MAE=%.1f cycles", name, C.RUL_MODEL_PATH, metrics["MAE"])
    return bundle


if __name__ == "__main__":
    train()
