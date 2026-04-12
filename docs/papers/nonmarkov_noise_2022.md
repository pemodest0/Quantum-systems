# Paper E: Characterization and control of non-Markovian quantum noise

Paper/workflow ID: `nonmarkov_noise_2022`

Category: `Memory diagnostics`

## Article Summary

The non-Markovian noise review frames the difference between memoryless effective dynamics and history-dependent dynamics. It motivates diagnostics such as trace-distance revivals, information backflow, negative time-local rates, and process-tensor approaches.

## Scientific Insights

The central insight is that a Lindblad equation is a model class, not a universal truth. Echo recovery, temporal correlations, or failure to predict multi-time data can reveal memory even when single-time decays look simple.

## Implemented Laboratory Model

Trace-distance revivals, negative time-local rates, Ramsey/echo disagreement, Markovian fit residuals.

## Direct Laboratory Comparison

Our synthetic benchmark created a memory-effective case and compared it against a Markovian fit. The Markovian model produced large residuals and failed echo predictions, giving concrete failure signatures for the lab.

## Project Lesson

A Lindblad model is sufficient only while it predicts the measured history-dependent data.

## Next Laboratory Use

If repeated FIDs, echo experiments, or tomography trajectories show revival or history dependence, escalate from simple Lindblad fitting to memory models or process tensors.

## Known Limitations

Benchmark is synthetic and minimal, not a reproduction of the full review.

## Key Metrics

- `failure_metrics.blp_measure`: `5.45706`
- `failure_metrics.markovian_fit_rmse`: `0.273341`

## Generated Figures

- `generated/figures/nonmarkov_noise_2022/lindblad_failure_signatures.png`
- `generated/figures/nonmarkov_noise_2022/markovian_vs_memory_ramsey_echo.png`
- `generated/figures/nonmarkov_noise_2022/time_local_rate_negative_intervals.png`
- `generated/figures/nonmarkov_noise_2022/trace_distance_revival.png`

## Canonical Artifacts

- Metrics: `outputs/repro/nonmarkov_noise_2022/latest/metrics.json`
- Config: `outputs/repro/nonmarkov_noise_2022/latest/config_used.json`
- Results: `outputs/repro/nonmarkov_noise_2022/latest/results.json`
