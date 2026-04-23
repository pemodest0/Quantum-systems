# Material-inspired full campaign

Generated at UTC: 2026-04-21T02:58:25.632898+00:00
Goal: compare several effective material families without overselling them as microscopic materials models.

## Literature guardrails

- Mohseni2008: https://doi.org/10.1063/1.3002335 -- Environment-assisted transport should be evaluated through target efficiency, not by coherence or spreading alone.
- Manzano2013: https://doi.org/10.1371/journal.pone.0057041 -- Useful transfer to a sink is not identical to internal redistribution through the network.
- MuelkenBlumen2011: https://doi.org/10.1016/j.physrep.2011.01.002 -- Different network families can support very different propagation behavior even when they have comparable size.

## What was measured

- Best family by useful arrival: ring aggregate with mean best arrival 0.563.
- Families that spread relatively well without above-average useful arrival: none.

## Agreement with literature

- This agrees with the literature if useful arrival and internal spreading are not treated as the same thing.
- A bottlenecked family should usually look worse than a family with alternate paths if the geometry matters.

## What is still not proven

- These are effective media, not microscopic materials models with fitted couplings.
- The first pass uses nearest-neighbor coupling only; long-range structure has not yet been tested.

## Derived table

| family | mean best arrival | mean spreading | mean mixing | mean gain |
| --- | --- | --- | --- | --- |
| molecular-wire-like chain | 0.478 | 23.616 | 1.643 | 0.001 |
| ring aggregate | 0.563 | 4.378 | 1.666 | 0.007 |
| disordered 2D sheet | 0.545 | 6.512 | 2.022 | 0.000 |
| bottleneck medium | 0.171 | 9.823 | 2.050 | 0.041 |
| clustered medium | 0.465 | 16.101 | 1.798 | 0.006 |
