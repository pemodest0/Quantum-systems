# Paper Card: Rebentrost 2009

## Source

Rebentrost, P.; Mohseni, M.; Kassal, I.; Lloyd, S.; Aspuru-Guzik, A. "Environment-assisted quantum transport." New Journal of Physics 11, 033003 (2009). DOI: https://doi.org/10.1088/1367-2630/11/3/033003

## Physical question

How does the interplay between Hamiltonian motion, disorder, and pure dephasing affect transport efficiency?

## Model

Open quantum transport model with coherent dynamics, disordered site energies, dephasing, and trapping. The paper uses photosynthetic and graph-like structures as examples.

## Central equations

```text
d rho / dt = -i[H, rho] + L_dephasing(rho) + L_trap(rho) + L_loss(rho)
```

## Observables

- transport efficiency.
- dephasing-dependent optimum.
- localization versus delocalization behavior.

## Main result

Moderate dephasing can improve transport when coherent dynamics alone suffers from localization or destructive interference. Very strong dephasing can suppress motion through a Zeno-like effect.

## Limitations

The optimum depends on network structure, disorder, trap placement, and timescale. It does not justify claiming noise assistance without a scan over noise strength.

## Relation with our lab

This is the direct guardrail for our phase diagrams: a credible assistance window should rise from the coherent baseline and eventually stop improving or fall at large phase scrambling.

