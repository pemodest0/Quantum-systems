# Paper Card: Plenio and Huelga 2008

## Source

Plenio, M. B.; Huelga, S. F. "Dephasing-assisted transport: quantum networks and biomolecules." New Journal of Physics 10, 113019 (2008). DOI: https://doi.org/10.1088/1367-2630/10/11/113019

## Physical question

Can local dephasing improve transport through a dissipative quantum network?

## Model

Quantum network with coherent couplings, local dephasing, and a transfer/output channel. The important control is the competition between coherent hopping and dephasing.

## Central equations

```text
d rho / dt = -i[H, rho] + sum_i gamma_i D[|i><i|]rho + output terms
D[L]rho = L rho L^\dagger - 1/2 {L^\dagger L, rho}
```

## Observables

- transport efficiency.
- dependence on dephasing strength.
- network population dynamics.

## Main result

There are regimes where local dephasing increases transport efficiency. The improvement is not unlimited; too much dephasing can suppress useful dynamics.

## Limitations

The result is not a universal law for every graph or every trap position. The mechanism depends on the structure of the Hamiltonian and the dissipative channels.

## Relation with our lab

This is the main reference for checking whether a nonzero `gamma_phi/J` optimum is physically plausible.

