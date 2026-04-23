# Entropy, Purity, Shannon Entropy, and Participation

Goal: read the information-theory observables without overclaiming.

## Purity

Purity is

```text
P(t) = Tr(rho(t)^2)
```

For a normalized state:

- `P = 1` means pure.
- smaller `P` means more mixed.

In an open system, dephasing usually reduces purity because it destroys phase information.

## Von Neumann entropy

Von Neumann entropy is

```text
S(t) = -Tr(rho log rho)
```

It measures mixedness of the quantum state. For a pure normalized state, `S = 0`. A larger value means the state contains more statistical uncertainty.

Important: if the observable is computed on graph-only normalized population, it describes the surviving excitation inside the graph, not the full target-plus-loss accounting.

## Shannon population entropy

Population Shannon entropy uses only site probabilities:

```text
H_pop(t) = -sum_i p_i log p_i
```

This ignores off-diagonal coherence. It measures how spread the population distribution is over sites.

## Participation ratio and IPR

The inverse participation ratio is often

```text
IPR(t) = sum_i p_i(t)^2
```

The participation ratio is

```text
PR(t) = 1 / IPR(t)
```

Interpretation:

- `PR close to 1`: localized on one site.
- larger `PR`: population spread across more sites.

## What these observables do not prove

Large population entropy or large participation ratio does not prove good transport. It only says the excitation is spread out. Good transport requires arrival at the chosen target channel.

Common mistake: "the wave spread, so transport improved." Correct reading: spreading is a mechanism candidate; target arrival is the success metric.

