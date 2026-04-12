# Paper H: GRAPE NMR optimal control

Paper/workflow ID: `grape_nmr_control_2005`

Category: `Optimal control`

## Article Summary

The GRAPE paper introduces gradient-based optimal control for NMR pulse design. It is the natural response to finite-pulse failures because it optimizes the full pulse shape under a modeled Hamiltonian rather than relying on ideal rectangular rotations.

## Scientific Insights

The central insight is that high-fidelity control is an optimization problem constrained by drift, control amplitudes, robustness requirements, and ensemble errors. Pulse design should include the physics that would otherwise appear as systematic gate error.

## Implemented Laboratory Model

GRAPE unitary optimization over detuning and RF-scale ensemble members.

## Direct Laboratory Comparison

Our reproduction directly compared a rectangular pulse to a GRAPE-optimized pulse on the spin-3/2 platform. The optimized pulse improved mean robustness-grid fidelity and fixed the failure mode exposed by Paper D.

## Project Lesson

Robust pulse design is necessary for high-fidelity quadrupolar spin-3/2 operations.

## Next Laboratory Use

After measuring real B0/B1 offsets and RF limits, train GRAPE pulses against those calibrated uncertainties and validate them with QST.

## Known Limitations

Optimization is synthetic and does not yet include measured hardware transfer functions.

## Key Metrics

- `optimization.final_training_mean_fidelity`: `0.991512`
- `robustness_grid.grape.mean`: `0.96249`

## Generated Figures

- `generated/figures/grape_nmr_control_2005/grape_fidelity_convergence.png`
- `generated/figures/grape_nmr_control_2005/optimized_controls.png`
- `generated/figures/grape_nmr_control_2005/rectangular_vs_grape_state_fidelity.png`
- `generated/figures/grape_nmr_control_2005/robustness_map.png`

## Canonical Artifacts

- Metrics: `outputs/repro/grape_nmr_control_2005/latest/metrics.json`
- Config: `outputs/repro/grape_nmr_control_2005/latest/config_used.json`
- Results: `outputs/repro/grape_nmr_control_2005/latest/results.json`
