# Paper G: Quadrupolar nuclei for NMR quantum information processing

Paper/workflow ID: `quadrupolar_qip_2012`

Category: `Encoded QIP`

## Article Summary

This paper reviews quantum information processing with quadrupolar nuclei in NMR. It treats a spin-3/2 nucleus as a four-level system that can encode two logical qubits and support pseudo-pure states, gates, and tomography.

## Scientific Insights

The important insight is the dual identity of the system: it is simultaneously a quadrupolar NMR object and an encoded two-qubit register. Product-operator decompositions make that connection explicit.

## Implemented Laboratory Model

Product-operator decompositions, pseudo-pure states, Grover benchmark, synthetic QST.

## Direct Laboratory Comparison

Our reproduction validated the mapping from spin operators to encoded two-qubit product operators and reproduced ideal Grover-style behavior under synthetic assumptions. This links the Na-23 spectroscopy code to quantum-information protocols.

## Project Lesson

Na-23 can be modeled both as quadrupolar NMR and as an encoded four-level QIP platform.

## Next Laboratory Use

Use this paper to decide how to label states, transitions, pseudo-pure preparations, and logical operations in future lab notes.

## Known Limitations

Ideal encoded operations are synthetic and require pulse-level implementation for experiments.

## Key Metrics

- `product_operator_decomposition.iz_nonzero_coefficients.IZ`: `0.5`
- `product_operator_decomposition.iz_nonzero_coefficients.ZI`: `1`
- `product_operator_decomposition.quadrupolar_traceless_nonzero_coefficients.ZZ`: `3`
- `product_operator_decomposition.iz_reconstruction_residual`: `0`
- `product_operator_decomposition.quadrupolar_reconstruction_residual`: `0`
- `grover_ideal.min_marked_population`: `1`

## Generated Figures

- `generated/figures/quadrupolar_qip_2012/grover_marked_state_populations.png`
- `generated/figures/quadrupolar_qip_2012/product_operator_decomposition.png`
- `generated/figures/quadrupolar_qip_2012/pseudopure_visibility.png`
- `generated/figures/quadrupolar_qip_2012/qst_noise_sensitivity.png`

## Canonical Artifacts

- Metrics: `outputs/repro/quadrupolar_qip_2012/latest/metrics.json`
- Config: `outputs/repro/quadrupolar_qip_2012/latest/config_used.json`
- Results: `outputs/repro/quadrupolar_qip_2012/latest/results.json`
