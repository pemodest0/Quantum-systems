# Modular Refinement Campaign

## Scientific Question

Does the modular two-community network keep a real dephasing-assisted transport window when the disorder and phase-scrambling grid is refined?

## Plain Reading

- `W/J` means local irregularity compared with coherent hopping strength.
- `gamma/J` means phase scrambling compared with coherent hopping strength.
- `arrival` means final population captured by the successful-arrival channel.
- `gain` means arrival at a given phase scrambling minus arrival with zero phase scrambling for the same graph and disorder realization.

## Main Numerical Result

- Simulated curve points: 9072.
- Numerical validation passed: True.
- Strongest mean gain: 0.096.
- Strongest disorder `W/J`: 0.7.
- Strongest phase scrambling `gamma/J`: 1.6.
- Two-peak candidates found: 0.

## Interpretation

The result is strong only if the gain is positive with a positive confidence interval and the high-scrambling end does not simply keep improving forever.

## Next Action

If the best point sits at the upper gamma boundary, extend the gamma grid. If it is internal and stable, use this as the refined modular-network claim.
