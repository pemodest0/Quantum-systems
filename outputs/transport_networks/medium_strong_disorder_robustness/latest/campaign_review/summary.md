# Strong-disorder robustness campaign

Generated at UTC: 2026-04-21T02:53:29.283464+00:00
Goal: compare chain, ring and 2D square under genuinely difficult disorder values using both mean arrival and ensemble spread.

## Literature guardrails

- Novo2016: https://doi.org/10.1038/srep18142 -- Robustness claims must be checked with disorder ensembles, not from single draws.
- Coutinho2022: https://doi.org/10.1038/s42005-022-00866-7 -- Network robustness under noise requires both mean performance and variability.
- Mohseni2008: https://doi.org/10.1063/1.3002335 -- Moderate dephasing can partially recover transport once disorder is significant.

## What was measured

- Best mean arrival: ring with 0.539.
- Best robustness by spread: ring with spread 0.039.

## Agreement with literature

- This agrees with the literature only if the ranking by mean is reported together with the ranking by spread.
- If the same medium wins both by mean and by spread, the robustness claim is materially stronger.

## What is still not proven

- A medium should not be called best from mean arrival alone if the ensemble spread is comparable to the mean separation.
- This is still an interactive campaign with 16 seeds, not the heaviest confirmatory run.

## Derived table

| medium | mean best arrival | mean spread | mean best phase | mean gain |
| --- | --- | --- | --- | --- |
| chain | 0.298 | 0.041 | 0.125 | 0.005 |
| ring | 0.539 | 0.039 | 0.225 | 0.028 |
| 2D square | 0.430 | 0.047 | 0.050 | 0.006 |
