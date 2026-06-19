# Battery Cell Investigation Case Study

_Generated: 2026-06-19 - synthetic factory/usage/failure data; no confidential data used._

## Selected Cell

Selected the highest-risk current queue item: **CELL-00032**.

| Field | Value |
| --- | --- |
| Lot / station | LOT-009 / ST-08 |
| Usage profile | thermal_stress |
| Risk tier | Critical |
| Failure probability | 1.0000 |
| Predicted SOH | 0.6606 |
| Last observed SOH | 0.5444 |
| Predicted remaining cycles | 0.0 |
| Model top driver | Accelerated capacity fade |
| Engineering follow-up | Pull cell for teardown; check anode lithium plating and electrolyte loss. |

## Peer Context

| Signal | Cell value | Fleet percentile | Why it matters |
| --- | --- | --- | --- |
| Capacity fade rate | 0.000876 | 100.0% | Higher fade rate indicates accelerated loss of usable capacity. |
| Resistance growth rate | 0.005989 | 97.5% | Rising resistance can point to aging, contact, tab-weld, or impedance-growth issues. |
| Peak temperature max | 54.0 C | 92.5% | Thermal exposure can accelerate degradation and needs sensor/protocol review. |
| Last observed SOH | 0.5444 | 0.8% | Low percentile means the cell sits among the weakest cells in the fleet. |

## Lot And Station Context

| Context | Escalation signal |
| --- | --- |
| Same lot average escalation rate | 33.3% |
| Same station average escalation rate | 9.5% |
| Same lot-station escalation rate | 66.7% |
| Same lot-station early degradation rate | 66.7% |

## Recent Cycle Window

| Window | SOH start | SOH end | Delta | Max rolling temp C |
| --- | --- | --- | --- | --- |
| Last 20 cycles | 0.5694 | 0.5444 | -0.0250 | 54.0 |

## Decision

1. Confirm the SOH estimate with a reference performance test.
2. Execute the recommended follow-up: Pull cell for teardown; check anode lithium plating and electrolyte loss.
3. Compare this cell with same-lot and same-station peers before deciding whether the issue is isolated or systemic.

## Boundary

This is a synthetic production-style investigation. It demonstrates the analysis loop, warehouse joins, peer comparison, and escalation writing. It does not claim a validated production false-positive rate without authorized real factory, usage, failure-label, and disposition data.
