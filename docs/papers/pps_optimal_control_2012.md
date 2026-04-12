# Paper I: Pseudo-pure states in a quadrupolar spin system

Paper/workflow ID: `pps_optimal_control_2012`

Category: `State preparation`

## Article Summary

This paper focuses on preparing pseudo-pure states in a quadrupolar spin system using optimal control. Pseudo-pure states are necessary because room-temperature NMR begins near a highly mixed thermal state with a small deviation component.

## Scientific Insights

The insight is that useful NMR quantum-information experiments operate on the deviation density matrix. State preparation is therefore about engineering the observable deviation component, not producing a truly pure thermodynamic state.

## Implemented Laboratory Model

Population averaging, GRAPE state preparation, gradient/dephasing step, QST validation.

## Direct Laboratory Comparison

Our implementation compared analytical population averaging and GRAPE-based preparation, followed by synthetic QST validation. Both reached near-perfect synthetic deviation fidelity under the modeled assumptions.

## Project Lesson

The lab has a reproducible state-preparation layer before control or tomography experiments.

## Next Laboratory Use

Use this layer before any encoded algorithm or control experiment: prepare the target pseudo-pure state, apply gradient/dephasing if needed, then validate by QST.

## Known Limitations

Synthetic preparation; real experiments need gradient, RF, and phase calibration.

## Key Metrics

- `grape_preparation.final_preparation_error`: `3.0698e-09`
- `grape_preparation.final_deviation_fidelity`: `1`

## Generated Figures

- `generated/figures/pps_optimal_control_2012/pps_grape_convergence.png`
- `generated/figures/pps_optimal_control_2012/pps_optimized_controls.png`
- `generated/figures/pps_optimal_control_2012/pps_population_profiles.png`
- `generated/figures/pps_optimal_control_2012/pps_qst_noise_sensitivity.png`

## Canonical Artifacts

- Metrics: `outputs/repro/pps_optimal_control_2012/latest/metrics.json`
- Config: `outputs/repro/pps_optimal_control_2012/latest/config_used.json`
- Results: `outputs/repro/pps_optimal_control_2012/latest/results.json`
