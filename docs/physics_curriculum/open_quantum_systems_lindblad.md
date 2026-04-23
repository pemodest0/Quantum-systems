# Open Quantum Systems and Lindblad Evolution

Goal: understand why the lab uses a master equation instead of only Schrodinger evolution.

## Closed system

For a closed system,

```text
d rho / dt = -i [H, rho]
```

This means the Hamiltonian `H` rotates the state coherently. No population is lost and no uncontrolled phase scrambling happens.

## Open system

Real systems are not perfectly isolated. They interact with surrounding degrees of freedom: phonons, electromagnetic noise, uncontrolled modes, measurement apparatus, or engineered noise.

A common Markovian model is the Lindblad master equation:

```text
d rho / dt = -i [H, rho] + sum_a (L_a rho L_a^\dagger - 1/2 {L_a^\dagger L_a, rho})
```

The first term is coherent motion. The sum is the environmental part. Each `L_a` is a jump operator describing one type of irreversible process.

## What Markovian means

Markovian means the environment has no long memory in the model. The future depends on the current `rho(t)`, not on the full previous history.

This is an approximation. It is useful for a first laboratory because it is controlled, stable, and easy to validate.

## Why Lindblad is used

The Lindblad form is designed to preserve valid density matrices when used correctly:

- trace is conserved if all channels are included.
- probabilities remain nonnegative within numerical tolerance.
- the state remains Hermitian.

## Lab validation checks

The simulation must check:

- trace closure: total population is not mysteriously created.
- nonnegative populations: diagonal entries should not become physically negative beyond tolerance.
- Hermiticity: `rho = rho^\dagger`.
- target plus loss accounting: population leaving the graph must go somewhere modeled.

Common mistake: treating Lindblad terms as "just friction". Different jump operators mean different physics. Dephasing, loss, and target arrival are not the same process.

