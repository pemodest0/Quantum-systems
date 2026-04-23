# Statistical Mechanics for Open Systems

Goal: connect open-system simulations with statistical-physics language.

## Ensemble

An ensemble is a set of repeated simulations with controlled random variation.

In this lab, a disorder ensemble means many random choices of site energies `epsilon_i` with the same disorder strength `W`.

Why it matters:

- one random disorder pattern can be misleading.
- the mean shows typical behavior.
- the spread shows how reliable the mean is.

## Mean and spread

For a metric `x_s` measured over seeds `s`,

```text
mean = average_s x_s
std = sqrt(average_s (x_s - mean)^2)
```

A larger mean is not enough. If spread is large, the result may not be stable.

## Entropy and coarse graining

Entropy can describe missing information. In the lab:

- von Neumann entropy measures mixedness of `rho`.
- Shannon population entropy measures spread of site probabilities.

They are related but not identical.

## Effective temperature warning

The current lab does not automatically simulate a thermal bath with detailed balance. Local dephasing is phase noise, not a full finite-temperature relaxation model.

Do not infer a material temperature unless the model explicitly includes thermal rates satisfying the right balance conditions.

## Irreversibility

Target arrival and loss are irreversible channels in the effective model. They turn coherent motion into accumulated outcomes.

Common mistake: calling `gamma_phi` a temperature. It is a phase scrambling rate. Temperature would require additional modeling.

