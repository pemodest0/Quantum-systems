# 2D target-position campaign

Generated at UTC: 2026-04-21T02:49:56.975900+00:00
Goal: test whether target placement stays important in a 2D medium.

## Literature guardrails

- Razzoli2021: https://doi.org/10.3390/e23010085 -- Target position is a first-order control variable for graph transport efficiency.
- Mohseni2008: https://doi.org/10.1063/1.3002335 -- Assistance by the environment is expected mainly when the coherent baseline is frustrated.
- Coutinho2022: https://doi.org/10.1038/s42005-022-00866-7 -- Robustness and geometry must be evaluated together, not from one best-case number.

## What was measured

- Best-ranked target: trap 0. Worst-ranked target: trap 3.
- Ranking gap between best and worst targets: 0.250.

## Agreement with literature

- This agrees with the literature if different target geometries remain distinguishable in the 2D medium.
- If the best phase-scrambling values differ between targets, geometry is not being washed out by dimensionality.

## What is still not proven

- This is still an effective 2D medium, not a microscopic material model.
- A ranking based on disorder-averaged best arrival compresses details that may still matter row by row.

## Derived table

| target index | disorder | best arrival | best phase scrambling |
| --- | --- | --- | --- |
| 0 | 0.40 | 0.603 | 0.000 |
| 0 | 0.60 | 0.562 | 0.000 |
| 0 | 0.80 | 0.518 | 0.000 |
| 0 | 1.00 | 0.462 | 0.000 |
| 3 | 0.40 | 0.284 | 0.800 |
| 3 | 0.60 | 0.286 | 0.800 |
| 3 | 0.80 | 0.287 | 0.800 |
| 3 | 1.00 | 0.288 | 0.800 |
| 5 | 0.40 | 0.392 | 0.000 |
| 5 | 0.60 | 0.368 | 0.100 |
| 5 | 0.80 | 0.360 | 0.400 |
| 5 | 1.00 | 0.351 | 0.400 |
| 10 | 0.40 | 0.404 | 0.000 |
| 10 | 0.60 | 0.411 | 0.000 |
| 10 | 0.80 | 0.418 | 0.000 |
| 10 | 1.00 | 0.419 | 0.000 |
