# Public Battery Dataset Expansion Plan

This plan identifies credible public datasets that could extend the real-data layer without committing large raw files to the repo. The recommendation is to add adapters and small derived validation summaries, not raw archives.

## Current Baseline: NASA PCoE Battery Aging Dataset

- Source: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- Download: https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip
- Data type: Li-ion charge, discharge, and impedance aging experiments at different temperatures.
- Likely features: discharge capacity, SOH, cycle index, voltage/current/temperature signals, impedance-derived health indicators.
- Mapping: strongest fit for SOH trend extraction, first cycle below 80% SOH, cycle-level degradation ingestion, and RUL-style targets.
- Caveats: raw archive is large enough to keep out of Git; not factory/field data; some cells are not clean monotonic fade cases without protocol review.
- Difficulty: already implemented.
- Worth adding before interview: yes, already present. The next improvement would be documenting protocol-level grouping more deeply.

## CALCE Battery Data

- Source: https://calce.umd.edu/battery-data
- Data type: open lithium-ion battery test data including full/partial cycling, storage, dynamic driving profiles, open-circuit voltage, and impedance. CALCE describes cylindrical, pouch, and prismatic form factors and LCO, LFP, and NMC chemistries.
- Likely features: cycle capacity, voltage/current/temperature traces, impedance measurements, storage-life conditions, dynamic usage profiles.
- Mapping: useful for SOH estimation, RUL prediction, accelerated degradation modeling, reliability analysis, and chemistry/protocol comparison.
- Licensing/access caveats: public academic data, but publications should cite the relevant CALCE articles and dataset-specific notes.
- Implementation difficulty: medium. It likely needs dataset-specific adapters because CALCE hosts several battery families and file layouts.
- Worth adding before interview: maybe. A small CS2-style adapter would strengthen cross-dataset credibility, but only if implemented cleanly with source citations and no raw data committed.

## Oxford Battery Degradation Dataset 1

- Source: https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac
- Data type: long-term cycling of 8 Kokam 740 mAh lithium-ion pouch cells; Oxford provides a `.mat` dataset, small example file, and readme.
- Likely features: cell-level cycle aging trajectories, capacity degradation, voltage and related cycling measurements depending on the `.mat` structure.
- Mapping: good for SOH trend validation, degradation curve comparison, and an additional `.mat` parser path independent of NASA.
- Licensing/access caveats: Oxford ORA lists terms of use; the full `.mat` file is large, so the repo should provide downloader instructions and commit only small summaries.
- Implementation difficulty: medium. Similar tooling to NASA helps, but the `.mat` schema is different.
- Worth adding before interview: not necessary unless time remains. A documented plan is enough; a rushed parser would be riskier than useful.

## Severson / MIT-Stanford Fast-Charging Cycle-Life Dataset

- Source: https://data.matr.io/
- Publication: https://storagex.stanford.edu/publications/accelerated-validation-new-materials-and-technologies/data-driven-prediction-battery
- Data type: 124 commercial LFP/graphite cells cycled to failure under fast-charging conditions, with cycle lives from roughly 150 to 2,300 cycles.
- Likely features: early-cycle discharge voltage curves, capacity trajectories, charge protocols, cycle life labels, train/test split metadata.
- Mapping: very strong for early-cycle RUL/cycle-life prediction and for comparing whether features from early cycles can classify high- versus low-life cells.
- Licensing/access caveats: Data.matr.io lists the dataset under CC BY 4.0. Raw files are too large for Git and should be downloaded locally or cached outside the repo.
- Implementation difficulty: medium to high. File sizes and nested structures are larger, and the modeling target is cycle life under fast-charge policies rather than factory escalation.
- Worth adding before interview: no full implementation needed before the interview. It is a high-value next dataset to mention because it maps well to RUL and fast-charge analytics.

## Recommended Sequence

1. Keep NASA as the implemented real-data validation layer.
2. Add CALCE next if the goal is broader chemistry/protocol coverage.
3. Add Oxford if the goal is another compact degradation benchmark with a different lab/source.
4. Add Severson after the interview if the goal is stronger early-cycle RUL modeling and fast-charge policy analysis.
