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

- Records: 1032
- Families: 7
- Maximum trace deviation: 6.883e-15
- Maximum population closure error: 6.883e-15
- Minimum state eigenvalue: -1.660e-15
- Numerics pass: True

## Highest mean target arrival

- chain: 0.506
- bottleneck: 0.467
- clustered: 0.466
- ring: 0.459
- square_lattice_2d: 0.446

## Highest mean quantum-minus-classical arrival

- clustered: 0.175
- bottleneck: 0.153
- ring: 0.145
- chain: 0.124
- square_lattice_2d: 0.091

## Scientific caution

- High entropy means more mixing, not automatically better transport.
- Strong transport requires target arrival, not only spreading.
- A quantum signature is not claimed when the classical control explains the arrival within 0.05 or the CI95 crosses zero.
- Fractal networks are included as an exploratory geometry front, not as a final classification claim.
