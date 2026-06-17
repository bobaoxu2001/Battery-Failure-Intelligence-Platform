# High-Risk Battery Cells - Daily Escalation Summary

_Generated: 2026-06-17 • synthetic data; no Apple confidential data used._

**32 cells** require engineering attention today (**24 Critical**, **7 High**, **1 other rule-based escalation(s)**).

## Queue composition by risk tier

| Risk tier | Cells |
| --- | --- |
| Critical | 24 |
| High | 7 |
| Medium | 1 |
| Low | 0 |
| **Total** | **32** |

_Medium/Low rows are in the queue because the failure-event record already flags them for escalation (`escalation_required = 1`), even though the model risk tier is below High._

## Top cells in the escalation queue

| Cell | Lot | Station | Risk | Fail prob | Pred SOH | Rem. cycles | Likely root cause | Recommended follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CELL-00032 | LOT-009 | ST-08 | Critical | 1.000 | 0.661 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00069 | LOT-001 | ST-06 | Critical | 1.000 | 0.627 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00074 | LOT-009 | ST-05 | Critical | 1.000 | 0.753 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00049 | LOT-003 | ST-01 | Critical | 0.998 | 0.714 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00060 | LOT-008 | ST-05 | Critical | 0.998 | 0.832 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00090 | LOT-001 | ST-01 | Critical | 0.996 | 0.748 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00037 | LOT-008 | ST-04 | Critical | 0.995 | 0.795 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00027 | LOT-009 | ST-08 | Critical | 0.995 | 0.766 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00003 | LOT-010 | ST-01 | Critical | 0.987 | 0.725 | 0 | Low state of health | Prioritise for replacement; confirm capacity with reference performance test. |
| CELL-00014 | LOT-009 | ST-02 | Critical | 0.986 | 0.764 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00051 | LOT-008 | ST-04 | Critical | 0.983 | 0.808 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00045 | LOT-011 | ST-07 | Critical | 0.977 | 0.785 | 3 | Test-station anomaly signal | Re-test on a reference station; audit station calibration drift. |
| CELL-00102 | LOT-001 | ST-05 | Critical | 0.944 | 0.777 | 0 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00019 | LOT-011 | ST-02 | Critical | 0.939 | 0.763 | 8 | Accelerated capacity fade | Pull cell for teardown; check anode lithium plating and electrolyte loss. |
| CELL-00117 | LOT-006 | ST-04 | Critical | 0.939 | 0.783 | 11 | Sustained thermal exposure | Review duty cycle thermal load; validate temperature sensor calibration. |

## Lots with the most escalations

| Lot | Escalated cells |
| --- | --- |
| LOT-010 | 6 |
| LOT-009 | 4 |
| LOT-001 | 3 |
| LOT-002 | 3 |
| LOT-003 | 3 |

## Recommended actions
1. Triage all **Critical** cells first; confirm SOH with a reference performance test.
2. For lots above the fleet escalation rate, hold the lot and open a factory-quality investigation.
3. Re-test any cell whose driver is a *test-station anomaly* on a reference station before scrapping.

_See `reports/escalation_report_sample.csv` for the full machine-readable queue._
