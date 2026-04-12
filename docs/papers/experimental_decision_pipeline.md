# Workflow: Experimental decision pipeline

Paper/workflow ID: `experimental_decision_pipeline`

Category: `Lab operations`

## Article Summary

The pipeline is not a paper; it is the operational synthesis of the papers. It prepares a state, validates QST, simulates or ingests DD coherences, reconstructs an effective spectrum, chooses a control sequence, and prepares comparison templates for real data.

## Scientific Insights

The insight is that research must become a decision loop. The lab should not only simulate papers; it should decide what to measure next and how to falsify or refine the model.

## Implemented Laboratory Model

Synthetic QST plus DD spectral inversion and candidate sequence scoring.

## Direct Laboratory Comparison

The current synthetic run selects CPMG-24 and records the status as waiting for lab data. Once real coherences arrive, the same pipeline reports residuals and decides whether the model is sufficient.

## Project Lesson

The paper reproductions now form a single operational decision loop.

## Next Laboratory Use

Use this as the default entry point for incoming experiments: fill the manifest, run the pipeline, inspect residuals, and update research memory.

## Known Limitations

Waiting for real lab data; current decision is synthetic.

## Key Metrics

- `state_preparation_summary.qst_fidelity`: `0.985594`
- `decision_summary.selected_predicted_coherence`: `0.989469`

## Generated Figures

- `generated/figures/experimental_decision_pipeline/control_sequence_decision.png`
- `generated/figures/experimental_decision_pipeline/dd_spectroscopy_fit.png`
- `generated/figures/experimental_decision_pipeline/reconstructed_noise_spectrum.png`
- `generated/figures/experimental_decision_pipeline/state_preparation_qst.png`

## Canonical Artifacts

- Metrics: `outputs/workflows/experimental_decision_pipeline/latest/metrics.json`
- Config: `outputs/workflows/experimental_decision_pipeline/latest/config_used.json`
- Results: `outputs/workflows/experimental_decision_pipeline/latest/results.json`
