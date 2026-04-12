# Paper N: Colored-noise spectroscopy by dynamical decoupling

Paper/workflow ID: `dd_noise_spectroscopy_2011`

Category: `DD spectroscopy`

## Article Summary

This paper uses dynamical decoupling not only to suppress noise but to measure its spectrum. Different pulse sequences sample different spectral bands, allowing reconstruction of colored noise from coherence measurements.

## Scientific Insights

The central insight is inversion: coherence decay under known filters can be converted into constraints on S(omega). The problem is ill-conditioned, so positivity and sequence coverage matter.

## Implemented Laboratory Model

Non-negative least-squares reconstruction from CPMG/UDD coherences.

## Direct Laboratory Comparison

Our NNLS reconstruction recovered the broad colored structure and localized a narrow spectral feature within the synthetic grid resolution. This method feeds the experimental-decision pipeline.

## Project Lesson

DD data can reconstruct colored spectra and feed control-sequence decisions.

## Next Laboratory Use

Collect coherence under a planned family of CPMG/UDD sequences, reconstruct the spectrum, then select the sequence predicted to preserve coherence best.

## Known Limitations

The inverse problem is ill-conditioned and depends on sequence coverage and pulse ideality.

## Key Metrics

- `reconstruction_summary.spectrum_correlation`: `0.922895`
- `reconstruction_summary.relative_spectrum_error`: `0.311457`

## Generated Figures

- `generated/figures/dd_noise_spectroscopy_2011/dd_coherence_fit.png`
- `generated/figures/dd_noise_spectroscopy_2011/dd_reconstructed_spectrum.png`
- `generated/figures/dd_noise_spectroscopy_2011/dd_sequence_sensitivity.png`
- `generated/figures/dd_noise_spectroscopy_2011/dd_spectrum_residual.png`

## Canonical Artifacts

- Metrics: `outputs/repro/dd_noise_spectroscopy_2011/latest/metrics.json`
- Config: `outputs/repro/dd_noise_spectroscopy_2011/latest/config_used.json`
- Results: `outputs/repro/dd_noise_spectroscopy_2011/latest/results.json`
