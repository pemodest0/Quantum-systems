# Paper J: Projected least-squares QPT

Paper/workflow ID: `projected_ls_qpt_2022`

Category: `Physical QPT`

## Article Summary

Projected least-squares QPT addresses the fact that raw process estimates from finite data can be non-physical. It projects estimates onto physically meaningful sets such as positive semidefinite and trace-preserving Choi matrices.

## Scientific Insights

The central insight is that physical constraints are not cosmetic. Enforcing complete positivity and trace preservation can reduce error and prevent impossible conclusions.

## Implemented Laboratory Model

Raw Choi least squares compared with PSD and CPTP projections.

## Direct Laboratory Comparison

Our synthetic benchmark showed raw Choi estimates with frequent physicality violations, while CPTP projection removed negative-eigenvalue violations and improved mean reconstruction error.

## Project Lesson

Projection reduces unphysical estimates and improves synthetic process reconstruction.

## Next Laboratory Use

Whenever process data are reconstructed from hardware, report both raw residuals and physicality-projected estimates.

## Known Limitations

Projection is a statistical post-processing layer; it cannot fix bad experimental design alone.

## Key Metrics

- `error_summary.cptp_choi_error.mean`: `0.176726`
- `physicality_summary.cptp_negative_fraction`: `0`

## Generated Figures

- `generated/figures/projected_ls_qpt_2022/choi_eigenvalues_raw_vs_pls.png`
- `generated/figures/projected_ls_qpt_2022/physicality_violations_vs_shots.png`
- `generated/figures/projected_ls_qpt_2022/ptm_reconstruction_comparison.png`
- `generated/figures/projected_ls_qpt_2022/qpt_error_distribution.png`

## Canonical Artifacts

- Metrics: `outputs/repro/projected_ls_qpt_2022/latest/metrics.json`
- Config: `outputs/repro/projected_ls_qpt_2022/latest/config_used.json`
- Results: `outputs/repro/projected_ls_qpt_2022/latest/results.json`
