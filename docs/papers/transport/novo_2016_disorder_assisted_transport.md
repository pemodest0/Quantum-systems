# Paper Card: Novo 2016

## Source

Novo, L.; Mohseni, M.; Omar, Y. "Disorder-assisted quantum transport in suboptimal decoherence regimes." Scientific Reports 6, 18142 (2016). DOI: https://doi.org/10.1038/srep18142

## Physical question

Can static disorder improve transport when decoherence is not already in the optimal regime?

## Model

Disordered Frenkel-exciton Hamiltonians on graph structures such as binary trees and hypercubes, with pure dephasing and transport efficiency measurements.

## Central equations

```text
H = sum_i epsilon_i |i><i| + sum_{i != j} J_ij |i><j|
d rho / dt = -i[H, rho] + L_dephasing(rho) + L_trap(rho)
```

## Observables

- transport efficiency versus disorder.
- transport efficiency versus dephasing.
- comparison between ordered and disordered networks.

## Main result

Disorder can assist transport in regimes where decoherence alone is suboptimal. Disorder is not always harmful, but its role is conditional.

## Limitations

The result is topology- and regime-dependent. It does not mean more disorder is always better.

## Relation with our lab

Use it to frame scans over `W/J`: disorder can be a control parameter, not only a nuisance.

