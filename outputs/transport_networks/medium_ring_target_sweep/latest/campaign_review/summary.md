# Ring target sweep campaign

Generated at UTC: 2026-04-21T02:25:30.901031+00:00
Goal: map how target placement changes useful arrival and the best environment strength on the same ring.

## Literature guardrails

- Razzoli2021: https://doi.org/10.3390/e23010085 -- Trap position changes transport efficiency on graphs and must be treated as a core variable.
- Rebentrost2009: https://doi.org/10.1088/1367-2630/11/3/033003 -- Environment-assisted transport should be diagnosed by comparing sink efficiency with and without dephasing.
- PlenioHuelga2008: https://doi.org/10.1088/1367-2630/10/11/113019 -- The environment should matter differently when the coherent baseline is favorable versus frustrated.

## What was measured

- Best-ranked target: trap 0. Worst-ranked target: trap 1.
- Ranking gap between best and worst targets: 0.078.

## Agreement with literature

- This agrees with the literature if the ranking is not flat and the best phase-scrambling values depend on the target.
- If the same target remains best across disorder values, target placement is acting as a first-order variable here.

## What is still not proven

- A ranking based on the mean over disorder compresses the details of each disorder row into one number per target.
- The present interactive run uses 16 seeds; a paper-grade confirmation would still need a heavier repeat.

## Derived table

| target index | disorder | best arrival | best phase scrambling |
| --- | --- | --- | --- |
| 0 | 0.60 | 0.654 | 0.000 |
| 0 | 0.80 | 0.608 | 0.000 |
| 0 | 1.00 | 0.557 | 0.000 |
| 0 | 1.20 | 0.513 | 0.200 |
| 1 | 0.60 | 0.517 | 0.600 |
| 1 | 0.80 | 0.511 | 0.600 |
| 1 | 1.00 | 0.502 | 0.600 |
| 1 | 1.20 | 0.490 | 0.600 |
| 2 | 0.60 | 0.545 | 0.600 |
| 2 | 0.80 | 0.541 | 0.600 |
| 2 | 1.00 | 0.536 | 0.600 |
| 2 | 1.20 | 0.529 | 0.600 |
| 3 | 0.60 | 0.581 | 0.800 |
| 3 | 0.80 | 0.582 | 0.800 |
| 3 | 1.00 | 0.583 | 0.600 |
| 3 | 1.20 | 0.583 | 0.600 |
