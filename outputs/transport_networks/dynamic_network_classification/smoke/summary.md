# Dynamic network classification campaign

Generated at UTC: 2026-04-21T07:54:46.067345+00:00
Profile: `smoke`

## What was tested

- Families: chain, complete, ring, star.
- Records: 32 dynamic signatures.
- Disorder grid: [0.0, 0.6].
- Phase-scrambling grid: [0.0, 0.2].

## What was measured

- Classification accuracy with topology + dynamics: 1.000.
- Classification accuracy with topology only: 1.000.
- Baseline majority accuracy: 0.250.
- Largest dephasing gain: 0.122 in `star` with target `near`.
- Useful dephasing candidates with gain >= 0.05: 20.
- Regime counts: {'mixed-crossover': 3, 'dephasing-assisted': 22, 'coherent-dominated': 7}.

## What the literature would expect

- Dephasing can help when coherent motion is trapped by interference or disorder, but strong dephasing can suppress transport.
- Target placement should matter in finite graphs and cannot be treated as a nuisance parameter.
- Disorder requires ensemble statistics; single-seed behavior is not enough for a strong claim.

## Current interpretation

- If topology + dynamics beats topology-only classification, the time evolution carries information beyond static graph metrics.
- If gains concentrate in specific families or target styles, the next campaign should refine those regions instead of expanding blindly.
- This is not a material simulation; it is an effective model for classifying transport mechanisms in finite networks.

## Critic report

- Level: pilot_only.
- Main concern: Smoke run validates the pipeline but is too small for scientific claims..
- Next action: Run profile pilot for all network families, then refine only separable families..

## Numerical checks

- Max trace deviation: 3.109e-15.
- Max population closure error: 3.220e-15.
- Minimum state eigenvalue: -8.293e-16.
