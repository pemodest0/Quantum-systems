# Paper D: Spin-3/2 quantum logical operations monitored by QST

Paper/workflow ID: `spin32_qlogic_qst_2005`

Category: `Selective control`

## Article Summary

This paper demonstrates spin-3/2 quadrupolar logical operations monitored by QST. Its relevance is not only the logic operation itself but the warning that finite pulse duration and quadrupolar evolution during the pulse can strongly affect the actual operation.

## Scientific Insights

The key insight is that a selective pulse is not automatically an ideal two-level gate embedded in a four-level system. During long pulses, the internal Hamiltonian keeps acting, and the intended transition-selective rotation can accumulate unwanted phases or leakage.

## Implemented Laboratory Model

Selective rectangular pulses with and without internal quadrupolar evolution.

## Direct Laboratory Comparison

Our benchmark compared pulses with and without internal quadrupolar evolution. The contrast was severe: the idealized model can look perfect while the physically evolved pulse fails. This made the later GRAPE reproduction necessary.

## Project Lesson

Ignoring quadrupolar evolution during pulses can destroy coherent gate fidelity.

## Next Laboratory Use

Do not trust rectangular selective-pulse designs without simulating the full Hamiltonian during the pulse. Use QST to check the actual state after the pulse.

## Known Limitations

Rectangular pulses are diagnostic baselines; optimized pulses are handled by the GRAPE layer.

## Key Metrics

- `fidelity_summary.min_operator_fidelity_with_quadrupolar`: `2.2414e-15`

## Generated Figures

- `generated/figures/spin32_qlogic_qst_2005/all_transition_fidelity_comparison.png`
- `generated/figures/spin32_qlogic_qst_2005/population_transfer_vs_duration.png`
- `generated/figures/spin32_qlogic_qst_2005/qst_density_monitor.png`
- `generated/figures/spin32_qlogic_qst_2005/selective_pulse_fidelity_vs_duration.png`

## Canonical Artifacts

- Metrics: `outputs/repro/spin32_qlogic_qst_2005/latest/metrics.json`
- Config: `outputs/repro/spin32_qlogic_qst_2005/latest/config_used.json`
- Results: `outputs/repro/spin32_qlogic_qst_2005/latest/results.json`
