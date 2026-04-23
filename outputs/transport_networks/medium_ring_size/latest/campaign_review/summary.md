# Ring size and symmetry campaign

Generated at UTC: 2026-04-21T02:17:16.780846+00:00
Goal: check whether the favorable/unfavorable target contrast survives changes in ring size.

## Literature guardrails

- PlenioHuelga2008: https://doi.org/10.1088/1367-2630/10/11/113019 -- Noise assistance depends on network symmetry and destructive interference.
- Razzoli2021: https://doi.org/10.3390/e23010085 -- Trap position and graph structure jointly determine transport efficiency.
- MuelkenBlumen2011: https://doi.org/10.1016/j.physrep.2011.01.002 -- Continuous-time quantum transport on networks can change qualitatively with topology and size.

## What was measured

- Mean unfavorable-target gain across sizes ranges from 0.082 to 0.140.
- Mean favorable-target gain across sizes ranges from 0.001 to 0.021.
- Unfavorable target positive-across-sizes status: yes.

## Agreement with literature

- This agrees with the literature if the unfavorable target keeps a positive gain while the favorable target stays near the coherent optimum.
- If both target types behave the same after averaging over disorder, the target-position effect is not structurally robust.

## What is still not proven

- These are disorder-averaged summaries, so finer structure at individual disorder values is compressed into one line per size.
- This campaign uses 12 seeds and is appropriate for interactive review, not the last confirmatory step.

## Derived table

| target type | N | mean best arrival | mean gain | mean best phase | mean spread |
| --- | --- | --- | --- | --- | --- |
| favorable | 6 | 0.677 | 0.021 | 0.200 | 0.046 |
| favorable | 8 | 0.578 | 0.005 | 0.075 | 0.056 |
| favorable | 10 | 0.487 | 0.001 | 0.050 | 0.083 |
| favorable | 12 | 0.391 | 0.009 | 0.113 | 0.027 |
| unfavorable | 6 | 0.640 | 0.086 | 0.600 | 0.025 |
| unfavorable | 8 | 0.507 | 0.140 | 0.600 | 0.017 |
| unfavorable | 10 | 0.411 | 0.109 | 0.500 | 0.016 |
| unfavorable | 12 | 0.341 | 0.082 | 0.400 | 0.022 |
