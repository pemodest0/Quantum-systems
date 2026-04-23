# Numerical Methods and Validation

Goal: know when a numerical result is trustworthy enough to discuss.

## Time evolution

The simulation evolves `rho(t)` under a master equation. Numerically, this means solving coupled differential equations for all matrix entries.

For `N` graph sites plus target and loss channels, the density matrix dimension grows. Larger systems become more expensive quickly.

## Basic validation

Every run should check:

- no NaN or infinite values.
- trace accounting closes within tolerance.
- populations are nonnegative within tolerance.
- final target arrival is between 0 and 1.
- coherence and entropy are finite.

## Grid resolution

A phase diagram is only as good as its grid. If a transition appears between two sampled values, refine locally before making a claim.

Example: if the chain crossover appears between `W/J = 0.70` and `0.80`, run a finer grid in that interval.

## Ensemble size

Small ensembles are pilots. They identify candidates. They do not prove robust physics.

Suggested language:

- 4 seeds: exploratory.
- 12-16 seeds: interactive campaign.
- 32-64 seeds: stronger validation for disorder-dependent claims.

## Claim discipline

Acceptable:

- "This campaign suggests a target-position effect."
- "The effect is stable across the sampled seeds."
- "This requires refinement before a strong claim."

Not acceptable:

- "This proves a new law."
- "This material behaves like the model" without material parameters.
- "Noise is always beneficial."

Common mistake: using the best point in a noisy scan as a discovery. A real candidate should survive nearby parameters and ensemble variation.

