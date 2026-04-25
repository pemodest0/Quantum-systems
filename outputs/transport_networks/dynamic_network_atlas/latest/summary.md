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

- Records: 14800
- Families: 10
- Maximum trace deviation: 1.266e-14
- Maximum population closure error: 1.266e-14
- Minimum state eigenvalue: -3.433e-15
- Numerics pass: True

## Highest mean target arrival

- ring: 0.534
- bottleneck: 0.524
- clustered: 0.524
- chain: 0.520
- square_lattice_2d: 0.481

## Highest mean quantum-minus-classical arrival

- chain: 0.181
- ring: 0.167
- clustered: 0.163
- bottleneck: 0.150
- sierpinski_carpet_like: 0.111

## Scientific caution

- High entropy means more mixing, not automatically better transport.
- Strong transport requires target arrival, not only spreading.
- A quantum signature is not claimed when the classical control explains the arrival within 0.05 or the CI95 crosses zero.
- Fractal networks are included as an exploratory geometry front, not as a final classification claim.
