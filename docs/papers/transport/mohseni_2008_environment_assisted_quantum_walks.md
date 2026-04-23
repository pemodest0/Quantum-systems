# Paper Card: Mohseni 2008

## Source

Mohseni, M.; Rebentrost, P.; Lloyd, S.; Aspuru-Guzik, A. "Environment-assisted quantum walks in photosynthetic energy transfer." Journal of Chemical Physics 129, 174106 (2008). DOI: https://doi.org/10.1063/1.3002335

## Physical question

Can environmental fluctuations improve energy-transfer efficiency in a photosynthetic-inspired quantum network instead of only destroying coherence?

## Model

Single-excitation transport on an effective excitonic network. The system includes coherent Hamiltonian motion, dephasing-like environmental action, and trapping/output channels.

## Central equations

```text
d rho / dt = -i[H, rho] + environmental terms + trapping terms
```

The paper is a foundation for the idea that a quantum walk can be helped by a controlled amount of environmental noise.

## Observables

- transfer efficiency.
- time-dependent populations.
- role of coherence and environmental action.

## Main result

Moderate environmental action can improve transfer in a network where purely coherent motion is not automatically optimal.

## Limitations

This does not prove that noise always helps. It is model-dependent and tied to network structure, trap placement, and environmental parameters.

## Relation with our lab

Use it as a guardrail for environment-assisted transport. Our lab must show a finite window, not just a single noisy point, before claiming assistance.

