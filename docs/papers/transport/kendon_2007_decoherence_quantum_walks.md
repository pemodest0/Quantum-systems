# Kendon 2007: Decoherence In Quantum Walks

## Source

Viv Kendon, `Decoherence in quantum walks: a review`, Mathematical Structures in Computer Science 17, 1169-1220 (2007). DOI: `10.1017/S0960129507006354`.

## Physical Question

How does non-unitary evolution change quantum-walk behavior?

## Model

Review of quantum walks with decoherence and other non-unitary effects.

## Central Claim

Decoherence is not only an error. In moderate amounts it can tune spreading and mixing, while excessive decoherence removes coherent quantum-walk behavior.

## Limitations

This is a review-level source, not a benchmark of our exact graph families or sink model.

## Relation with our lab

This is a guardrail for interpreting `gamma_phi/J`: it is the phase-scrambling strength compared with coherent coupling. We should look for a useful intermediate region and avoid saying that more dephasing is always better.

## Benchmark In Our Suite

`kendon_2007.decoherence_as_a_tunable_quantum_walk_parameter`: matched when useful nonzero dephasing and high-dephasing suppression are both resolved.
