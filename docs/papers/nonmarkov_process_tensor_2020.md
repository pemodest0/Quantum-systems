# Paper L: Non-Markovian process tensor characterization and control

Paper/workflow ID: `nonmarkov_process_tensor_2020`

Category: `Multi-time memory`

## Article Summary

The process-tensor paper demonstrates multi-time characterization and control in non-Markovian settings. Rather than describing a process by one fixed channel, it models how interventions at different times interact with memory.

## Scientific Insights

The central insight is that memory is operational: the best next control can depend on the previous controls. A single Markovian channel cannot represent that dependence.

## Implemented Laboratory Model

Synthetic process tensor versus Markovian channel for multi-time prediction and control selection.

## Direct Laboratory Comparison

Our synthetic process-tensor benchmark predicted multi-time probabilities far better than a fixed Markovian model and selected a different, better control sequence.

## Project Lesson

Memory-aware prediction can select different and better controls than Markovian modeling.

## Next Laboratory Use

Escalate to process-tensor experiments only after simpler DD, QST, and Lindblad models fail; it is powerful but experimentally expensive.

## Known Limitations

Synthetic correlated dephasing only; real process-tensor tomography is experimentally expensive.

## Key Metrics

- `prediction_summary.improvement_factor`: `14.7084`
- `control_summary.true_control_advantage`: `0.365222`

## Generated Figures

- `generated/figures/nonmarkov_process_tensor_2020/process_tensor_control_landscape.png`
- `generated/figures/nonmarkov_process_tensor_2020/process_tensor_echo_witness.png`
- `generated/figures/nonmarkov_process_tensor_2020/process_tensor_prediction_scatter.png`
- `generated/figures/nonmarkov_process_tensor_2020/process_tensor_rmse_by_length.png`

## Canonical Artifacts

- Metrics: `outputs/repro/nonmarkov_process_tensor_2020/latest/metrics.json`
- Config: `outputs/repro/nonmarkov_process_tensor_2020/latest/config_used.json`
- Results: `outputs/repro/nonmarkov_process_tensor_2020/latest/results.json`
