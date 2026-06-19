"""Train the retrospective failure-risk / escalation classifier.

Target:  ``escalation_required`` (cell needs engineering escalation).
Approach: Logistic Regression baseline vs. RandomForestClassifier on a
stratified cell-level split; the higher-F1 model is kept. Reports precision,
recall, F1, ROC-AUC and the confusion matrix.

This is a retrospective investigation model: it intentionally uses lifetime
features such as ``final_soh`` to help compare pass/fail cells and identify
likely failure drivers after enough lifecycle data exists. It is not the
early-warning model.

Run as a module::

    python -m src.models.train_failure_classifier
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def train() -> C.ModelBundle:
    config.ensure_dirs()
    frame = pd.read_csv(config.CELL_FEATURES_CSV)

    positives = int(frame["escalation_required"].sum())
    if positives < 4 or positives > len(frame) - 4:
        raise ValueError(
            f"Failure classifier needs both classes well represented "
            f"(got {positives}/{len(frame)} escalations). Increase data scale "
            f"(unset BFI_QUICK) or adjust the synthetic generator."
        )

    X_tr, X_te, y_tr, y_te = C.stratified_split(frame, C.FAILURE_FEATURES, "escalation_required")

    candidates = {
        "LogisticRegression": C.logistic_baseline(),
        "RandomForest": C.random_forest_classifier(),
    }

    best = None
    for name, est in candidates.items():
        est.fit(X_tr, y_tr)
        proba = est.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = C.classification_metrics(y_te, pred, proba)
        log.info("FAIL %-18s P=%.3f R=%.3f F1=%.3f AUC=%.3f",
                 name, metrics["precision"], metrics["recall"], metrics["f1"], metrics["roc_auc"])
        if best is None or metrics["f1"] > best[2]["f1"]:
            best = (name, est, metrics)

    name, est, metrics = best
    importance = C.importance_table(est, X_te, y_te, C.FAILURE_FEATURES)
    bundle = C.ModelBundle(
        name="retrospective_failure_classifier", target="escalation_required", features=C.FAILURE_FEATURES,
        estimator=est, metrics=metrics, importance=importance, algorithm=name,
    )
    bundle.save(C.FAILURE_MODEL_PATH)
    log.info("Saved failure classifier (%s) -> %s | F1=%.3f AUC=%.3f",
             name, C.FAILURE_MODEL_PATH, metrics["f1"], metrics["roc_auc"])
    return bundle


if __name__ == "__main__":
    train()
