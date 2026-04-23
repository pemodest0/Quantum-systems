# Dynamic Network Atlas

This atlas compares finite network families through open quantum transport signatures.

## What was measured

- Target arrival: population accumulated in the target arrival channel.
- Hitting time: first time the target channel crosses the chosen threshold.
- Coherence, entropy, purity, Shannon entropy, participation ratio and IPR.
- Spreading diagnostics: mean squared displacement and front width when coordinates exist.
- Quantum minus classical arrival on the same graph, target, loss and final time.
- Deterministic physical regime labels from explicit thresholds.

## Numerical status

- Records: 24
- Families: 3
- Maximum trace deviation: 2.220e-15
- Maximum population closure error: 2.220e-15
- Minimum state eigenvalue: -7.262e-16
- Numerics pass: True

## Highest mean target arrival

- chain: 0.417
- ring: 0.408
- random_geometric: 0.234

## Highest mean quantum-minus-classical arrival

- ring: 0.172
- chain: 0.112
- random_geometric: -0.011

## Scientific caution

- High entropy means more mixing, not automatically better transport.
- Strong transport requires target arrival, not only spreading.
- A quantum signature is not claimed when the classical control explains the arrival within 0.05 or the CI95 crosses zero.
- Fractal networks are included as an exploratory geometry front, not as a final classification claim.
