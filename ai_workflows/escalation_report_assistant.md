# AI Assistant — Engineering Escalation Summary Writer

> Reusable LLM assistant. Turns raw model outputs / the escalation queue into a
> concise, decision-ready escalation summary for engineering leadership. This is
> the human-language layer on top of `generate_escalation_report.py`.

## When to use
The daily pipeline produced `reports/escalation_report_sample.csv`. A reliability
lead needs a tight write-up they can paste into a standup or an email — not a
spreadsheet dump.

## Inputs
- `reports/escalation_report_sample.csv` (cell_id, lot_id, station_id,
  failure_probability, predicted_soh, predicted_remaining_cycles,
  likely_root_cause, recommended_follow_up)
- `dashboards/tableau_extracts/factory_lot_quality.csv` (for lot/station context)

## What good output looks like (the assistant's job)
1. **Headline** — one sentence: how many cells, how many Critical, the single
   biggest theme (e.g. "thermal-driven fade concentrated in LOT-007").
2. **Top offenders** — 3–5 cells, each as: `CELL | risk | root cause | action`.
3. **Systemic signal** — call out any lot or station that is over-represented
   (a process problem, not isolated cells). Quantify it.
4. **Recommended actions** — ranked, specific, owner-assignable.
5. **Watch list** — Medium-risk cells trending worse but not yet escalated.

## Tone & rules
- Lead with the decision, not the data. ≤ 200 words for the headline + actions.
- Every claim ties to a number from the CSV (probability, SOH, remaining cycles).
- Separate **confirmed** (failure event logged) from **predicted** (model only).
- Group by root cause so engineering can batch the response.
- Never invent cells, lots, or part numbers; synthetic data only.

## Template
```
ESCALATION SUMMARY — <date>
Headline: <N> cells flagged (<C> Critical). Dominant theme: <theme>.

Top offenders:
  • <cell> — <risk> — <root cause> — <action>
  • ...

Systemic signal:
  <lot/station> shows <metric> (<value> vs fleet <value>) → <interpretation>.

Recommended actions (ranked):
  1. <action> — owner: <team>
  2. ...

Watch list: <cells trending worse, not yet escalated>
```

## Example headline (from a real pipeline run)
> "32 cells flagged (24 Critical). Dominant theme: accelerated capacity fade in
> fast-charge-heavy cells; LOT-level escalation rate concentrated in two lots —
> recommend holding those lots pending teardown of the top 3 Critical cells."
