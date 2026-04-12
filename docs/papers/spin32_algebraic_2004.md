# Paper B: Algebraic description of spin 3/2 dynamics in NMR

Paper/workflow ID: `spin32_algebraic_2004`

Category: `Spin-3/2 algebra`

## Article Summary

The algebraic spin-3/2 paper gives an operator-level description of quadrupolar NMR dynamics. It is directly aligned with this project because our platform is a four-level spin-3/2 system, and the paper's formalism maps naturally into Hilbert-space and Liouville-space propagation.

## Scientific Insights

The key insight is that spin-3/2 NMR is not just four unrelated levels. The algebra organizes RF rotations, quadrupolar evolution, coherence orders, and detection pathways into a structured model that can be tested numerically.

## Implemented Laboratory Model

Hilbert evolution, Liouville-space superoperators, coherence-order pathways, and B0/B1 sensitivity.

## Direct Laboratory Comparison

Our reproduction directly compared Hilbert and Liouville propagation and found agreement at numerical precision. This supports using Liouville-space objects later for dissipators, superoperators, and process-level modeling.

## Project Lesson

The Liouville formalism is numerically consistent with Hilbert propagation and ready for dissipative extensions.

## Next Laboratory Use

Use this formalism when translating experimental pulse sequences into code: define the operator basis first, then compare predicted coherence pathways with measured spectra or tomography amplitudes.

## Known Limitations

Synthetic dynamics only; experiment-specific pulse calibration is not inferred.

## Key Metrics

- `hilbert_vs_liouville.max_abs_fid_error`: `2.5455e-17`

## Generated Figures

- `generated/figures/spin32_algebraic_2004/b0_b1_energy_map.png`
- `generated/figures/spin32_algebraic_2004/coherence_order_pathways.png`
- `generated/figures/spin32_algebraic_2004/hilbert_vs_liouville_fid.png`
- `generated/figures/spin32_algebraic_2004/superoperator_factorization_error.png`

## Canonical Artifacts

- Metrics: `outputs/repro/spin32_algebraic_2004/latest/metrics.json`
- Config: `outputs/repro/spin32_algebraic_2004/latest/config_used.json`
- Results: `outputs/repro/spin32_algebraic_2004/latest/results.json`
