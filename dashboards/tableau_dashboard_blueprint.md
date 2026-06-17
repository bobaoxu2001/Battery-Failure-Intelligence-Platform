# Tableau Dashboard Blueprint — Battery Failure Intelligence

> **Tableau Desktop is not required to run this project.** The pipeline exports
> flat, dashboard-ready CSV extracts to `dashboards/tableau_extracts/` that drop
> straight into Tableau (Text File connection), Excel, Power BI, or any BI tool.
> Static PNG mockups of the key pages are rendered to
> `dashboards/screenshots_or_mockups/`.

## Data sources (extracts)
| Extract CSV | Grain | Powers page |
| --- | --- | --- |
| `executive_battery_health.csv` | one row / cell | Pages 1, 4 |
| `factory_lot_quality.csv` | lot × station | Page 2 |
| `engineering_root_cause.csv` | usage_profile × driver | Page 3 |
| `escalation_queue.csv` | escalated cells | Page 4 |

Suggested relationships in Tableau: join all extracts on `cell_id` /
`lot_id` / `station_id` as needed; or keep them as separate data sources, one
per dashboard page (simplest).

---

## Page 1 — Executive Battery Health Overview
**Audience:** engineering leadership. **Question:** *How healthy is the fleet and
where is the risk?*

KPIs (BANs / big numbers):
- Total cells, % High+Critical risk, mean predicted SOH, count below 80% SOH.

Charts:
- **Fleet by risk tier** — bar, `COUNT(cell_id)` by `risk_tier`
  (color: Low→green, Medium→amber, High→orange, Critical→red).
- **SOH vs remaining cycles** — scatter, `predicted_soh` (y) vs
  `predicted_remaining_cycles` (x), color = `failure_probability`, ref line at
  SOH = 0.80.
- **Risk by usage profile** — stacked bar, `usage_profile` × `risk_tier`.

Filters: `lot_id`, `station_id`, `usage_profile`, `risk_tier`.
Fields: `cell_id, lot_id, station_id, usage_profile, last_soh, predicted_soh,
predicted_remaining_cycles, failure_probability, risk_tier`.

---

## Page 2 — Factory Lot Quality
**Audience:** factory / process engineering. **Question:** *Which lots and
stations are producing weaker cells?*

Charts:
- **Escalation rate by lot** — bar sorted desc, `escalation_rate` by `lot_id`,
  ref line at fleet-average escalation rate.
- **Lot × station heatmap** — `avg_final_soh` (or `thermal_anomaly_rate`) colored
  cells, rows = `lot_id`, cols = `station_id` (spot a bad station within a lot).
- **Anomaly mix** — stacked bar of `thermal_anomaly_rate` /
  `impedance_spike_rate` / `early_degradation_rate` by lot.

Filters: `lot_id`, `station_id`.
Fields: `lot_id, station_id, num_cells, avg_final_soh, avg_capacity_fade_rate,
escalation_rate, early_degradation_rate, thermal_anomaly_rate, impedance_spike_rate`.

---

## Page 3 — Engineering Root Cause Analysis
**Audience:** reliability / failure-analysis engineers. **Question:** *What is
driving degradation, and for which usage population?*

Charts:
- **Driver frequency** — bar, `cells` by `top_risk_driver`.
- **Driver × usage profile** — matrix, `cells` colored, rows = `top_risk_driver`,
  cols = `usage_profile`.
- **Fade vs resistance growth** — scatter, `avg_capacity_fade_rate` vs
  `avg_resistance_growth_rate`, size = `cells`, color = `avg_failure_probability`.

Filters: `usage_profile`, `top_risk_driver`.
Fields: `usage_profile, top_risk_driver, cells, avg_capacity_fade_rate,
avg_resistance_growth_rate, avg_failure_probability`.

---

## Page 4 — Escalation Queue
**Audience:** on-call engineer / daily standup. **Question:** *What needs action
today?*

Charts:
- **Escalation table** — sortable: `cell_id, lot_id, station_id, risk_tier,
  failure_probability, predicted_soh, predicted_remaining_cycles, top_risk_driver`,
  sorted by `failure_probability` desc; conditional formatting on risk tier.
- **Escalations by lot** — bar to expose a systemic lot.
- **Top driver split** — pie/bar of `top_risk_driver` across the queue.

Filters: `risk_tier`, `lot_id`, `top_risk_driver`.
Fields: all columns of `escalation_queue.csv`.

---

## Design conventions
- Risk color scale fixed across pages: Low `#2e7d32`, Medium `#f9a825`, High
  `#ef6c00`, Critical `#c62828`.
- SOH reference line at **0.80** (end-of-life) on every SOH axis.
- Every page footer: *"Synthetic data — no Apple confidential data used."*
- Refresh model: pipeline regenerates extracts daily; in Tableau, point the data
  sources at `dashboards/tableau_extracts/` and refresh the extract.
