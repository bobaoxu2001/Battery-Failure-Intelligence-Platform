"""Summarise model performance + explainability into a Markdown report.

Loads the three trained model bundles and writes
``reports/model_performance_summary.md`` containing:
  * a metrics table for SOH, RUL and the failure classifier,
  * the failure classifier confusion matrix,
  * top feature importances (SHAP if available, else permutation importance),
  * the leading drivers of high-risk degradation.

Run as a module::

    python -m src.models.evaluate_models
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src import config
from src.models import _common as C
from src.utils.logging_utils import get_logger

log = get_logger(__name__)


def _importance_md(bundle: C.ModelBundle, n: int = 6) -> str:
    if bundle.importance is None or bundle.importance.empty:
        return "_No importance available._"
    top = bundle.importance.head(n)
    method = top["method"].iloc[0]
    lines = [f"Top drivers ({method}):", "", "| Feature | Importance |", "| --- | --- |"]
    for _, r in top.iterrows():
        lines.append(f"| `{r['feature']}` | {r['importance']:.4f} |")
    return "\n".join(lines)


def build_report() -> str:
    config.ensure_dirs()
    soh = C.ModelBundle.load(C.SOH_MODEL_PATH)
    rul = C.ModelBundle.load(C.RUL_MODEL_PATH)
    fail = C.ModelBundle.load(C.FAILURE_MODEL_PATH)

    cm = fail.metrics["confusion_matrix"]
    quick = " (quick mode)" if config.QUICK_MODE else ""

    md = f"""# Model Performance Summary{quick}

_Generated: {date.today().isoformat()} • all data synthetic; no Apple confidential data used._

## 1. State of Health (SOH) regression
- **Algorithm:** {soh.algorithm}
- **Target:** `soh_current` = discharge_capacity / initial_capacity
- **Validation:** cell-grouped hold-out ({int(config.TEST_SIZE*100)}% of cells)

| Metric | Value |
| --- | --- |
| MAE  | {soh.metrics['MAE']:.4f} |
| RMSE | {soh.metrics['RMSE']:.4f} |
| R²   | {soh.metrics['R2']:.3f} |

{_importance_md(soh)}

## 2. Remaining Useful Life (RUL) regression
- **Algorithm:** {rul.algorithm}
- **Target:** `remaining_cycles` until SOH < {config.SOH_EOL_THRESHOLD:.0%}
- **Validation:** cell-grouped hold-out

| Metric | Value |
| --- | --- |
| MAE  | {rul.metrics['MAE']:.1f} cycles |
| RMSE | {rul.metrics['RMSE']:.1f} cycles |
| R²   | {rul.metrics['R2']:.3f} |

{_importance_md(rul)}

## 3. Failure-risk classification
- **Algorithm:** {fail.algorithm}
- **Target:** `escalation_required` (engineering escalation needed)
- **Validation:** stratified cell-level hold-out

| Metric | Value |
| --- | --- |
| Precision | {fail.metrics['precision']:.3f} |
| Recall    | {fail.metrics['recall']:.3f} |
| F1        | {fail.metrics['f1']:.3f} |
| ROC-AUC   | {fail.metrics['roc_auc']:.3f} |

Confusion matrix (rows = actual, cols = predicted):

|            | Pred 0 | Pred 1 |
| ---------- | ------ | ------ |
| **Actual 0** | {cm[0][0]} | {cm[0][1]} |
| **Actual 1** | {cm[1][0]} | {cm[1][1]} |

{_importance_md(fail)}

## 4. Leading drivers of high-risk degradation
Across the failure classifier, the dominant degradation drivers are the
engineered fade/resistance/thermal features — consistent with the physics of
lithium-ion ageing (capacity fade + impedance growth accelerated by thermal and
fast-charge stress). These same drivers populate the `top_risk_driver` column of
the escalation queue so each flagged cell carries a likely root cause.
"""
    out = config.REPORTS_DIR / "model_performance_summary.md"
    out.write_text(md, encoding="utf-8")
    log.info("Wrote %s", out)
    return md


if __name__ == "__main__":
    build_report()
