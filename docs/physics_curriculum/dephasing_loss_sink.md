# Dephasing, Loss, and Target Arrival

Goal: separate three processes that are often confused.

## Phase scrambling: `gamma_phi`

Phase scrambling, also called local dephasing, destroys phase relations between sites without directly removing population from the graph.

A local dephasing operator is

```text
L_i = sqrt(gamma_phi) |i><i|
```

Physical meaning: the environment keeps shaking the local phase of site `i`. Populations may remain, but interference is weakened.

In figures, `gamma_phi/J` means "phase scrambling rate compared with coherent hopping strength".

## Loss: `Gamma`

Loss removes the excitation into uncontrolled channels.

A loss operator can be written as

```text
L_loss,i = sqrt(Gamma_i) |lost><i|
```

Physical meaning: the excitation disappeared from the useful network and did not arrive at the target.

Loss is bad for target arrival unless the model is studying decay itself.

## Target arrival channel: `kappa`

The target arrival channel is the modeled successful capture of the excitation from a chosen trap site.

```text
L_target = sqrt(kappa) |target><trap_site|
```

The lab previously used the word "sink". In plain language, this is the successful arrival bucket. It is not automatically a physical drain in every real material; it is an effective way to measure transport to a desired site.

In figures, `kappa/J` means "target capture rate compared with coherent hopping strength".

## Why target arrival is measured cumulatively

The target population is accumulated:

```text
eta(T) = rho_target,target(T)
```

This is a success probability at final time `T`. It answers: "How much excitation reached the desired channel by the end?"

## Key distinction

- Dephasing changes interference.
- Loss destroys useful excitation.
- Target arrival records success.

Common mistake: calling every irreversible channel a sink. In this lab, "target arrival" is useful output; "loss" is failure output.

