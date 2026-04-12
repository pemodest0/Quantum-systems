# Paper F: Multipass quantum process tomography

Paper/workflow ID: `multipass_qpt_2024`

Category: `Hardware QPT`

## Article Summary

The multipass QPT paper studies process tomography where the same process is applied repeatedly. This can amplify process signatures relative to SPAM and sampling noise, improving characterization in some regimes.

## Scientific Insights

The key insight is experimental design: changing the number of passes changes the information content of the data. Repeated application is not just redundant measurement; it can expose weak process errors.

## Implemented Laboratory Model

Single-qubit PTM reconstruction with single-pass and multipass protocols.

## Direct Laboratory Comparison

Our one-qubit synthetic prototype compared single-pass and multipass PTM reconstruction under synthetic SPAM/readout/shot noise. The best multipass setting substantially reduced the mean reconstruction error.

## Project Lesson

Repeated blocks can amplify weak process signatures and improve reconstruction.

## Next Laboratory Use

For gate-model hardware access, use multipass protocols as an optional amplification layer after basic QPT and GST are working.

## Known Limitations

One-qubit synthetic prototype; not yet tied to a real backend.

## Key Metrics

- `process.ptm_frobenius_error_target_to_actual`: `0.0504287`
- `monte_carlo.shots`: `512`
- `monte_carlo.seed_count`: `60`
- `monte_carlo.single_pass_error.mean`: `0.215744`
- `monte_carlo.single_pass_error.std`: `0.0386803`
- `monte_carlo.single_pass_error.median`: `0.210698`

## Generated Figures

- `generated/figures/multipass_qpt_2024/error_vs_passes.png`
- `generated/figures/multipass_qpt_2024/ptm_comparison.png`
- `generated/figures/multipass_qpt_2024/shot_noise_sweep.png`
- `generated/figures/multipass_qpt_2024/single_vs_multipass_error_distribution.png`

## Canonical Artifacts

- Metrics: `outputs/repro/multipass_qpt_2024/latest/metrics.json`
- Config: `outputs/repro/multipass_qpt_2024/latest/config_used.json`
- Results: `outputs/repro/multipass_qpt_2024/latest/results.json`
