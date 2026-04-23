# Scientific validation report

Generated at UTC: 2026-04-21T23:30:33.111395+00:00
Profile: `smoke`

## Hypothesis

Dynamic signatures of open quantum transport can classify finite network families and identify when dephasing helps or hurts target arrival.

## Method

- Row split is kept only as an optimistic/debugging control.
- Group split is the scientific default: records from the same graph instance cannot appear in train and test at the same time.
- A classical continuous-time rate model is run on the same graphs as a baseline.
- Physical metrics are reported with mean, spread, standard error, and 95% confidence interval.

## Main results

- Open signatures: 72.
- Group-split combined accuracy: 0.967.
- Group-split baseline accuracy: 0.667.
- Classical-only group accuracy: 0.733.
- Mean strongest dephasing gain: 0.126.
- Strong-effect criterion met: True.
- Scientific verdict: `promising_but_not_final`.

## Paper reproduction score

- Matched: ['Mulken/Blumen: closed-walk return probability depends on topology.', 'Razzoli: target/trap placement changes transport efficiency.', 'Mohseni/Plenio/Rebentrost: nonzero dephasing can improve target arrival.'].
- Failed: [].
- Uncertain: ['Mohseni/Plenio/Rebentrost: high-noise suppression was not resolved in this grid.'].

## Limitations

- This report does not turn the previous exploratory run into a final claim.
- Confirmation requires the heavier profile if the smoke/pilot result remains promising.
- A result is not called quantum-specific unless it beats the classical control under group split.

## Next recommended campaign

Refine `erdos_renyi + unweighted + far target` with the confirm profile only if group-split and classical-control criteria remain positive in pilot mode.
