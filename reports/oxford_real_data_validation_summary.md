# Oxford Real Battery Data Validation

_Generated: 2026-06-20._

This report adds a second real public battery-aging source beyond NASA. It is used as cross-dataset parser and degradation-coverage evidence, not as production accuracy proof.

- Source dataset: Oxford Battery Degradation Dataset 1
- Official upstream: https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac
- DOI: 10.5287/bodleian:KO2kdmYGg
- Dataset description: long-term cycling of 8 Kokam 740 mAh lithium-ion pouch cells
- Run source mode: official full Oxford .mat archive
- Parsed cells: 8
- Parsed cycle snapshots: 519

## Cell-Level Degradation Summary

| Cell | Snapshots | Cycle range | Initial Ah | Final Ah | Capacity loss | First <80% SOH | Max discharge temp C | Corr(cycle, capacity) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cell1 | 78 | 0-8200 | 0.739 | 0.561 | 24.1% | 5800 | 41.8 | -0.986 |
| Cell2 | 73 | 0-7700 | 0.735 | 0.545 | 25.8% | 5000 | 42.0 | -0.986 |
| Cell3 | 76 | 0-8100 | 0.735 | 0.566 | 23.0% | 6300 | 41.5 | -0.992 |
| Cell4 | 47 | 0-5100 | 0.734 | 0.581 | 20.8% | 4800 | 42.5 | -0.990 |
| Cell5 | 46 | 0-5000 | 0.735 | 0.456 | 38.0% | 5000 | 42.8 | -0.910 |
| Cell6 | 46 | 0-5000 | 0.733 | 0.579 | 21.0% | 4600 | 42.9 | -0.996 |
| Cell7 | 77 | 0-8100 | 0.729 | 0.583 | 20.0% | 8000 | 42.9 | -0.994 |
| Cell8 | 76 | 0-8100 | 0.728 | 0.559 | 23.2% | 6400 | 41.9 | -0.996 |

## Boundary

Oxford validates a different lab, cell form factor, and test structure than NASA. The adapter intentionally normalizes only shared cycle-level degradation fields so the project can compare public sources without pretending they share a factory schema.
