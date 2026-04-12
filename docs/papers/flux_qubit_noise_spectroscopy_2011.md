# Paper O: Flux-qubit noise spectroscopy through DD

Paper/workflow ID: `flux_qubit_noise_spectroscopy_2011`

Category: `Hardware noise spectroscopy`

## Article Summary

This paper applies DD noise spectroscopy to a superconducting flux qubit and estimates a 1/f-like noise spectrum. It matters for this project because it shows that the DD spectroscopy logic is not platform-specific.

## Scientific Insights

The insight is portability: if the control filters and coherence model are known, the same inverse logic can apply to NMR spins or superconducting qubits, with platform-specific calibration.

## Implemented Laboratory Model

CPMG peak-filter estimates fitted to a synthetic 1/f^alpha spectrum.

## Direct Laboratory Comparison

Our synthetic flux-qubit-like benchmark estimated the exponent alpha from peak-filter samples. It validates the repository's hardware-facing direction beyond Na-23.

## Project Lesson

The spectroscopy layer is platform-independent in structure.

## Next Laboratory Use

Use this as the bridge when Ygor has access to gate-model quantum hardware: treat coherence experiments as spectral probes, not only as benchmark scores.

## Known Limitations

Synthetic flux-qubit-like data; not hardware-acquired data.

## Key Metrics

- `spectroscopy_summary.estimated_alpha`: `0.739918`
- `spectroscopy_summary.alpha_abs_error`: `0.0400821`

## Generated Figures

- `generated/figures/flux_qubit_noise_spectroscopy_2011/flux_coherence_vs_pulse_count.png`
- `generated/figures/flux_qubit_noise_spectroscopy_2011/flux_filter_peak_map.png`
- `generated/figures/flux_qubit_noise_spectroscopy_2011/flux_power_law_fit.png`
- `generated/figures/flux_qubit_noise_spectroscopy_2011/flux_spectrum_peak_estimates.png`

## Canonical Artifacts

- Metrics: `outputs/repro/flux_qubit_noise_spectroscopy_2011/latest/metrics.json`
- Config: `outputs/repro/flux_qubit_noise_spectroscopy_2011/latest/config_used.json`
- Results: `outputs/repro/flux_qubit_noise_spectroscopy_2011/latest/results.json`
