"""Train the early-warning failure classifier.

Target: ``escalation_required`` (eventual engineering escalation).
Feature boundary: first 50 cycles only, plus factory/test condition context.
This model is intentionally separate from the retrospective failure model so
features such as ``final_soh`` and full-life degradation rates cannot leak the
outcome into an early-warning use case.

Run as a module::

    python -m src.models.train_early_warning_classifier
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def train() -> C.ModelBundle:
    config.ensure_dirs()
    frame = pd.read_csv(config.EARLY_WARNING_FEATURES_CSV)

    positives = int(frame["escalation_required"].sum())
    if positives < 4 or positives > len(frame) - 4:
        raise ValueError(
            f"Early-warning classifier needs both classes well represented "
            f"(got {positives}/{len(frame)} escalations)."
        )

    X_tr, X_te, y_tr, y_te = C.stratified_split(frame, C.EARLY_WARNING_FEATURES, "escalation_required")

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
        log.info("EARLY %-15s P=%.3f R=%.3f F1=%.3f AUC=%.3f",
                 name, metrics["precision"], metrics["recall"], metrics["f1"], metrics["roc_auc"])
        if best is None or metrics["f1"] > best[2]["f1"]:
            best = (name, est, metrics)

    name, est, metrics = best
    importance = C.importance_table(est, X_te, y_te, C.EARLY_WARNING_FEATURES)
    bundle = C.ModelBundle(
        name="early_warning_failure_classifier",
        target="escalation_required",
        features=C.EARLY_WARNING_FEATURES,
        estimator=est,
        metrics=metrics,
        importance=importance,
        algorithm=name,
    )
    bundle.save(C.EARLY_WARNING_MODEL_PATH)
    build_report(bundle)
    log.info("Saved early-warning classifier (%s) -> %s | F1=%.3f AUC=%.3f",
             name, C.EARLY_WARNING_MODEL_PATH, metrics["f1"], metrics["roc_auc"])
    return bundle


def build_report(bundle: C.ModelBundle | None = None) -> str:
    if bundle is None:
        bundle = C.ModelBundle.load(C.EARLY_WARNING_MODEL_PATH)
    cm = bundle.metrics["confusion_matrix"]
    top = bundle.importance.head(8) if bundle.importance is not None else pd.DataFrame()
    lines = [
        "# Early-Warning Failure Model",
        "",
        f"_Generated: {date.today().isoformat()}._",
        "",
        "This model predicts eventual escalation from the first 50 cycles plus factory/test condition context. It is separate from the retrospective investigation model so lifetime-only fields cannot leak into early-warning decisions.",
        "",
        "## Feature Boundary",
        "",
        "- Allowed: first-50-cycle SOH/resistance/temperature/voltage summaries, acceptance-test settings, station peer context.",
        "- Excluded: `final_soh`, full-life `cycle_count`, lifetime peak temperature, full-life fade rate, failure labels, and post-outcome fields.",
        "",
        "## Holdout Metrics",
        "",
        f"- Algorithm: {bundle.algorithm}",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Precision | {bundle.metrics['precision']:.3f} |",
        f"| Recall | {bundle.metrics['recall']:.3f} |",
        f"| F1 | {bundle.metrics['f1']:.3f} |",
        f"| ROC-AUC | {bundle.metrics['roc_auc']:.3f} |",
        "",
        "Confusion matrix (rows = actual, cols = predicted):",
        "",
        "|            | Pred 0 | Pred 1 |",
        "| ---------- | ------ | ------ |",
        f"| **Actual 0** | {cm[0][0]} | {cm[0][1]} |",
        f"| **Actual 1** | {cm[1][0]} | {cm[1][1]} |",
        "",
        "## Top First-Window Drivers",
        "",
        "| Feature | Importance |",
        "| --- | --- |",
    ]
    if top.empty:
        lines.append("| _No importance available_ |  |")
    else:
        for _, row in top.iterrows():
            lines.append(f"| `{row['feature']}` | {row['importance']:.4f} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "Use this model for triage while cells are still early in life. Use the retrospective model for post-failure investigation, pass/fail comparison, and engineering root-cause analysis.",
    ]
    md = "\n".join(lines) + "\n"
    config.EARLY_WARNING_REPORT.write_text(md, encoding="utf-8")
    return md


if __name__ == "__main__":
    train()
