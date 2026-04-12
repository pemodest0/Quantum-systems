# Paper M: Experimental noise filtering by quantum control

Paper/workflow ID: `noise_filtering_control_2014`

Category: `DD filtering`

## Article Summary

This paper treats quantum control as noise filtering. Pulse sequences such as Ramsey, Hahn, CPMG, and UDD shape the spectral response of the qubit or spin to environmental noise.

## Scientific Insights

The key insight is spectral selectivity. Control sequences are filters in frequency space, so preserving coherence means aligning the filter with low-noise regions or rejecting dominant noise bands.

## Implemented Laboratory Model

Ramsey, Hahn, CPMG, and UDD filter functions under synthetic dephasing spectra.

## Direct Laboratory Comparison

Our benchmark computed filter functions and coherences under synthetic noise. It showed strong coherence gain from DD relative to Ramsey, establishing the basis for spectroscopy and control selection.

## Project Lesson

Control can suppress noise by shifting filter sensitivity away from dominant spectral weight.

## Next Laboratory Use

Use filter-function plots to choose initial DD sequences before attempting full noise-spectrum inversion.

## Known Limitations

Ideal instantaneous pulses; finite-pulse errors must be added before lab claims.

## Key Metrics

- `simulation.total_time_s`: `0.0012`
- `simulation.frequency_min_hz`: `10`
- `simulation.frequency_max_hz`: `3.0000e+04`
- `simulation.sequence_count`: `7`
- `summary.ramsey_coherence`: `0.609315`
- `summary.best_coherence`: `0.998123`

## Generated Figures

- `generated/figures/noise_filtering_control_2014/coherence_vs_control_sequence.png`
- `generated/figures/noise_filtering_control_2014/filter_peak_tracking.png`
- `generated/figures/noise_filtering_control_2014/noise_spectrum_and_filters.png`
- `generated/figures/noise_filtering_control_2014/time_domain_switching_functions.png`

## Canonical Artifacts

- Metrics: `outputs/repro/noise_filtering_control_2014/latest/metrics.json`
- Config: `outputs/repro/noise_filtering_control_2014/latest/config_used.json`
- Results: `outputs/repro/noise_filtering_control_2014/latest/results.json`
