# Paper C: Relaxation dynamics in a quadrupolar NMR system using QST

Paper/workflow ID: `qst_relaxation_2008`

Category: `QST relaxation`

## Article Summary

This paper studies relaxation dynamics in a quadrupolar NMR system using quantum state tomography. Instead of inferring relaxation only from spectra or envelopes, it reconstructs density matrices over time and extracts rates from the evolution of populations and coherences.

## Scientific Insights

The major insight is identifiability: tomography separates population relaxation and coherence decay more directly than a single FID spectrum. It also exposes phase errors and reconstruction instability that a magnitude spectrum could hide.

## Implemented Laboratory Model

Synthetic trajectories, seven-phase QST, rate extraction, noise stress tests.

## Direct Laboratory Comparison

Our synthetic workflow reproduces the structure of the protocol: generate state trajectories, simulate QST signals, reconstruct density matrices, and fit rates. The noiseless recovery works essentially exactly, while noisy tests show how uncertainty propagates into fitted rates.

## Project Lesson

QST can identify population and coherence decay rates beyond spectrum-only fitting.

## Next Laboratory Use

This should be the template for the first serious experimental validation: collect the seven-phase tomography series at multiple delay times and compare reconstructed density-matrix trajectories to the synthetic model.

## Known Limitations

Uses synthetic tomography signals; real extraction requires experimental amplitude calibration.

## Key Metrics

- `noiseless_reconstruction.mean_fidelity`: `1`
- `noiseless_reconstruction.gamma_population_estimate`: `52`

## Generated Figures

- `generated/figures/qst_relaxation_2008/density_element_decay.png`
- `generated/figures/qst_relaxation_2008/extracted_rate_vs_true.png`
- `generated/figures/qst_relaxation_2008/phase_error_sensitivity.png`
- `generated/figures/qst_relaxation_2008/tomography_fidelity_vs_noise.png`

## Canonical Artifacts

- Metrics: `outputs/repro/qst_relaxation_2008/latest/metrics.json`
- Config: `outputs/repro/qst_relaxation_2008/latest/config_used.json`
- Results: `outputs/repro/qst_relaxation_2008/latest/results.json`
