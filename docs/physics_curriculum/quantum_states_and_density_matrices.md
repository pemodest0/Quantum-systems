# Quantum States and Density Matrices

Goal: understand what the simulation stores when it evolves a quantum excitation.

## Pure state

A pure quantum state is written as

```text
|psi> = sum_i c_i |i>
```

Here `|i>` means "the excitation is at site `i`". The complex number `c_i` is an amplitude. The population at site `i` is

```text
p_i = |c_i|^2
```

Population is a probability. Amplitude is not a probability. Amplitudes can interfere because they have phase.

## Density matrix

The density matrix is

```text
rho = |psi><psi|
```

for a pure state. Its matrix elements are

```text
rho_ij = c_i c_j*
```

The diagonal part `rho_ii` gives populations. The off-diagonal part `rho_ij`, with `i != j`, stores coherence between sites.

## Mixed state

An open system interacts with an environment. Then the state may be a statistical mixture:

```text
rho = sum_a p_a |psi_a><psi_a|
```

This is why the lab evolves `rho(t)` instead of only `|psi(t)>`. A density matrix can represent both coherent quantum motion and classical uncertainty.

## Trace

The trace is the sum of diagonal elements:

```text
Tr(rho) = sum_i rho_ii
```

If the simulation includes every possible destination, trace should stay close to one. If the graph-only block excludes target arrival and loss channels, the graph-only trace can decrease because population left that block.

## How this maps to the lab

- `node populations`: diagonal entries on physical sites.
- `coherence`: off-diagonal entries.
- `target arrival`: population accumulated in the successful arrival channel.
- `loss`: population that left through uncontrolled channels.
- `full-state observable`: computed using every modeled state.
- `graph-normalized observable`: computed only on physical sites after renormalizing surviving graph population.

Common mistake: reading a large off-diagonal coherence as automatically good. Coherence can help, but it can also create destructive interference and trap amplitude away from the target.

