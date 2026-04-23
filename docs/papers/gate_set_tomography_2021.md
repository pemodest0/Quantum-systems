# Paper K: Gate set tomography

Paper/workflow ID: `gate_set_tomography_2021`

Category: `SPAM-aware tomography`

## Primary Reference

Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.

## Article Summary

Gate-set tomography models state preparation, gates, and measurements self-consistently. It avoids assuming that SPAM operations are ideal, which is often false in real hardware and can bias ordinary QPT.

## Scientific Insights

The key insight is that errors are gauge-structured. Direct gate matrices are not always uniquely meaningful, so predictive probabilities and held-out likelihoods are safer comparison targets.

## Implemented Laboratory Model

Minimal GST-like fitting of gates, preparation, and measurement through sequence probabilities.

## Direct Comparison with the Published Reference

Our minimal GST-like benchmark compared ideal-SPAM gate-only fitting with self-consistent fitting. The GST model greatly improved held-out prediction accuracy.

## Interpretation for the Present Study

Predictive probabilities are safer than direct gate parameters because GST has gauge freedom.

## Experimental Implication

Use GST when hardware data show that preparation/readout errors cannot be ignored or when ordinary QPT gives inconsistent gate estimates.

## Current Deviations from the Published Reference

Minimal benchmark, not a full pyGSTi-level implementation.

## Key Metrics

- `prediction_summary.heldout_improvement_factor`: `8.59956`
- `prediction_summary.heldout_rmse_gst`: `0.00761847`

## Figure Guide

### Figure 1. Gate-Matrix Residuals after GST Fitting

![Gate-Matrix Residuals after GST Fitting](../../outputs/repro/gate_set_tomography_2021/latest/figures/gst_gate_matrix_residuals.png)

- Summary: The estimated gate matrices are compared with the target predictive model to show where residual structure remains after GST fitting.
- Interpretation: In this laboratory, the figure is used to characterize gates predictively when SPAM and gauge issues matter. It should be read together with the matching metrics.json and results.json files, because visual agreement alone is not treated as sufficient evidence.
- Reference: Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.

### Figure 2. Gauge-Dependent SPAM Parameters in GST

![Gauge-Dependent SPAM Parameters in GST](../../outputs/repro/gate_set_tomography_2021/latest/figures/gst_gauge_dependent_spam.png)

- Summary: Preparation and measurement parameters are shown in a way that makes their gauge dependence explicit.
- Interpretation: In this laboratory, the figure is used to characterize gates predictively when SPAM and gauge issues matter. It should be read together with the matching metrics.json and results.json files, because visual agreement alone is not treated as sufficient evidence.
- Reference: Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.

### Figure 3. Held-Out Predictive Performance of GST

![Held-Out Predictive Performance of GST](../../outputs/repro/gate_set_tomography_2021/latest/figures/gst_heldout_predictions.png)

- Summary: The GST model is evaluated on held-out sequence probabilities that were not used directly in the fitting step.
- Interpretation: In this laboratory, the figure is used to characterize gates predictively when SPAM and gauge issues matter. It should be read together with the matching metrics.json and results.json files, because visual agreement alone is not treated as sufficient evidence.
- Reference: Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.

### Figure 4. GST Prediction Error versus Sequence Length

![GST Prediction Error versus Sequence Length](../../outputs/repro/gate_set_tomography_2021/latest/figures/gst_prediction_by_sequence_length.png)

- Summary: Prediction error is tracked as the calibration sequences become longer and more sensitive to coherent and incoherent gate errors.
- Interpretation: In this laboratory, the figure is used to characterize gates predictively when SPAM and gauge issues matter. It should be read together with the matching metrics.json and results.json files, because visual agreement alone is not treated as sufficient evidence.
- Reference: Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.


## Canonical Artifacts

- Metrics: `outputs/repro/gate_set_tomography_2021/latest/metrics.json`
- Config: `outputs/repro/gate_set_tomography_2021/latest/config_used.json`
- Results: `outputs/repro/gate_set_tomography_2021/latest/results.json`
