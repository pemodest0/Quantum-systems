# Paper K: Gate set tomography

Paper/workflow ID: `gate_set_tomography_2021`

Category: `SPAM-aware tomography`

## Article Summary

Gate-set tomography models state preparation, gates, and measurements self-consistently. It avoids assuming that SPAM operations are ideal, which is often false in real hardware and can bias ordinary QPT.

## Scientific Insights

The key insight is that errors are gauge-structured. Direct gate matrices are not always uniquely meaningful, so predictive probabilities and held-out likelihoods are safer comparison targets.

## Implemented Laboratory Model

Minimal GST-like fitting of gates, preparation, and measurement through sequence probabilities.

## Direct Laboratory Comparison

Our minimal GST-like benchmark compared ideal-SPAM gate-only fitting with self-consistent fitting. The GST model greatly improved held-out prediction accuracy.

## Project Lesson

Predictive probabilities are safer than direct gate parameters because GST has gauge freedom.

## Next Laboratory Use

Use GST when hardware data show that preparation/readout errors cannot be ignored or when ordinary QPT gives inconsistent gate estimates.

## Known Limitations

Minimal benchmark, not a full pyGSTi-level implementation.

## Key Metrics

- `prediction_summary.heldout_improvement_factor`: `8.59956`
- `prediction_summary.heldout_rmse_gst`: `0.00761847`

## Generated Figures

- `generated/figures/gate_set_tomography_2021/gst_gate_matrix_residuals.png`
- `generated/figures/gate_set_tomography_2021/gst_gauge_dependent_spam.png`
- `generated/figures/gate_set_tomography_2021/gst_heldout_predictions.png`
- `generated/figures/gate_set_tomography_2021/gst_prediction_by_sequence_length.png`

## Canonical Artifacts

- Metrics: `outputs/repro/gate_set_tomography_2021/latest/metrics.json`
- Config: `outputs/repro/gate_set_tomography_2021/latest/config_used.json`
- Results: `outputs/repro/gate_set_tomography_2021/latest/results.json`
