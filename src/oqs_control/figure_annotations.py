from __future__ import annotations

import hashlib
import json
import time
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as patches


ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_STATE_PATH = ROOT / ".figure_annotation_state.json"

SOURCE_REFERENCES: dict[str, str] = {
    "internal_validation_baseline": "Internal baseline for spin-3/2 Na-23 operators, Hamiltonians, Liouvillian consistency, and synthetic spectra.",
    "na23_relaxometry_2023": 'Song, Y. et al. "23Na relaxometry: An overview of theory and applications." Magnetic Resonance Letters 3(2), 150--174 (2023). DOI: 10.1016/j.mrl.2023.04.001.',
    "spin32_algebraic_2004": 'Tanase, C. and Boada, F. E. "Algebraic description of spin 3/2 dynamics in NMR experiments." Journal of Magnetic Resonance 173(2), 236--253 (2005). DOI: 10.1016/j.jmr.2004.12.009.',
    "qst_relaxation_2008": 'Auccaise, R. et al. "A study of the relaxation dynamics in a quadrupolar NMR system using Quantum State Tomography." Journal of Magnetic Resonance 192(1), 17--26 (2008). DOI: 10.1016/j.jmr.2008.01.009.',
    "spin32_qlogic_qst_2005": 'Bonk, F. A. et al. "Quantum logical operations for spin 3/2 quadrupolar nuclei monitored by quantum state tomography." Journal of Magnetic Resonance 175(2), 226--234 (2005). DOI: 10.1016/j.jmr.2005.04.009.',
    "nonmarkov_noise_2022": 'White, G. "Characterization and control of non-Markovian quantum noise." Nature Reviews Physics 4, 287 (2022). DOI: 10.1038/s42254-022-00446-2.',
    "multipass_qpt_2024": 'Stanchev, S. G. and Vitanov, N. V. "Multipass quantum process tomography." Scientific Reports 14(1), 18185 (2024). DOI: 10.1038/s41598-024-68353-3.',
    "quadrupolar_qip_2012": 'Teles, J. et al. "Quantum information processing by nuclear magnetic resonance on quadrupolar nuclei." Philosophical Transactions of the Royal Society A 370(1976), 4770--4793 (2012). DOI: 10.1098/rsta.2011.0365.',
    "grape_nmr_control_2005": 'Khaneja, N. et al. "Optimal control of coupled spin dynamics: Design of NMR pulse sequences by gradient ascent algorithms." Journal of Magnetic Resonance 172(2), 296--305 (2005). DOI: 10.1016/j.jmr.2004.11.004.',
    "pps_optimal_control_2012": 'Tan, Y.-P. et al. "Preparing Pseudo-Pure States in a Quadrupolar Spin System Using Optimal Control." Chinese Physics Letters 29(12), 127601 (2012). DOI: 10.1088/0256-307X/29/12/127601.',
    "projected_ls_qpt_2022": 'Surawy-Stepney, T. et al. "Projected Least-Squares Quantum Process Tomography." Quantum 6, 844 (2022). DOI: 10.22331/q-2022-10-20-844.',
    "gate_set_tomography_2021": 'Nielsen, E. et al. "Gate Set Tomography." Quantum 5, 557 (2021). DOI: 10.22331/q-2021-10-05-557.',
    "nonmarkov_process_tensor_2020": 'White, G. A. L. et al. "Demonstration of non-Markovian process characterisation and control on a quantum processor." Nature Communications 11, 5301 (2020). DOI: 10.1038/s41467-020-20113-3.',
    "noise_filtering_control_2014": 'Soare, A. et al. "Experimental noise filtering by quantum control." Nature Physics 10(11), 825--829 (2014). DOI: 10.1038/nphys3115.',
    "dd_noise_spectroscopy_2011": 'Alvarez, G. A. and Suter, D. "Measuring the spectrum of colored noise by dynamical decoupling." Physical Review Letters 107(23), 230501 (2011). DOI: 10.1103/PhysRevLett.107.230501.',
    "flux_qubit_noise_spectroscopy_2011": 'Bylander, J. et al. "Noise spectroscopy through dynamical decoupling with a superconducting flux qubit." Nature Physics 7(7), 565--570 (2011). DOI: 10.1038/nphys1994.',
    "experimental_decision_pipeline": "Internal workflow synthesis of Papers C, D, M, and N for laboratory decision support.",
}

SOURCE_ROLES: dict[str, str] = {
    "internal_validation_baseline": "certify the physical consistency of the spin-3/2 platform before any later claim",
    "na23_relaxometry_2023": "replace envelope-only fitting by an interpretable quadrupolar spectral-density picture",
    "spin32_algebraic_2004": "bridge operator algebra, Hilbert propagation, and Liouville superoperators",
    "qst_relaxation_2008": "identify population and coherence decay rates with tomography instead of spectrum-only fitting",
    "spin32_qlogic_qst_2005": "expose finite-pulse failure modes before trusting selective quadrupolar control",
    "nonmarkov_noise_2022": "decide when a simple Lindblad model stops being defensible",
    "multipass_qpt_2024": "measure whether repeated process blocks improve tomography under SPAM and shot noise",
    "quadrupolar_qip_2012": "reinterpret the Na-23 spin-3/2 nucleus as an encoded two-qubit information processor",
    "grape_nmr_control_2005": "replace fragile rectangular pulses with robust optimized controls",
    "pps_optimal_control_2012": "prepare pseudo-pure states before running control or tomography protocols",
    "projected_ls_qpt_2022": "enforce physicality in process reconstruction instead of trusting raw least-squares inversion",
    "gate_set_tomography_2021": "characterize gates predictively when SPAM and gauge issues matter",
    "nonmarkov_process_tensor_2020": "escalate to multi-time memory models when Markovian channels fail",
    "noise_filtering_control_2014": "treat pulse sequences as spectral filters over the environmental noise",
    "dd_noise_spectroscopy_2011": "invert DD coherence measurements into an effective colored-noise spectrum",
    "flux_qubit_noise_spectroscopy_2011": "check that the spectroscopy layer transfers beyond the Na-23 NMR platform",
    "experimental_decision_pipeline": "turn preparation, QST, spectroscopy, and control scoring into one operational loop",
}

BASE_FIGURE_NOTES: dict[str, str] = {
    "nmr_open_simulation.png": "Dense Liouvillian propagation checks trace preservation, Hermiticity, positivity, and entropy trends for the Na-23 open-system model.",
    "nmr_synthetic_dissipation_fit.png": "A synthetic target FID is fitted back to effective dephasing and relaxation rates to validate the inverse problem under ideal conditions.",
    "nmr_validation_suite.png": "Repeated noisy synthetic trials quantify how robust the effective-rate recovery remains as measurement quality degrades.",
    "nmr_reference_dissipation_fit.png": "The current reference TNT FID is compared against the effective open-system model as a diagnostic fit, not as final microscopic identification.",
    "nmr_tomography_pipeline.png": "Synthetic signal generation, spectral extraction, and seven-phase tomography are combined to validate the end-to-end Na-23 QST pipeline.",
    "open_qubit_demo.png": "A generic two-level open-system model visualizes purity loss, entropy growth, and free-energy-like trends outside the NMR-specific setting.",
}

COMPARISON_FIGURE_NOTES: dict[str, str] = {
    "comparison_figure_count.png": "Counts how many plot artifacts each reproduction or workflow contributes to the repository.",
    "comparison_quality_scores.png": "Collects normalized fidelity-like and correlation-like metrics across the reproduced papers.",
    "comparison_improvement_factors.png": "Compares how much each method improves its own target quantity, such as fidelity, prediction quality, or control advantage.",
    "comparison_error_metrics.png": "Places representative residual or reconstruction errors on one logarithmic panel to show where mismatch remains largest.",
}

OUTPUT_FIGURE_SUMMARIES: dict[str, dict[str, str]] = {
    "internal_validation_baseline": {
        "internal_validation_baseline.png": "The baseline panel consolidates commutator checks, Hermiticity checks, transition positions, and physical-state diagnostics for the Na-23 spin-3/2 model.",
    },
    "na23_relaxometry_2023": {
        "envelope_residuals.png": "Residual curves compare the empirical biexponential envelopes with the reduced spectral-density model over the same relaxation window.",
        "phenomenological_vs_redfield_decay.png": "The MATLAB-derived biexponential decay envelopes are overlaid with the reduced Redfield-inspired curves for the three quadrupolar transitions.",
        "rates_vs_tau_c.png": "The effective relaxation rates are tracked versus correlation time to show the crossover between fast-motion and slow-motion quadrupolar regimes.",
        "spectral_density_regimes.png": "Reduced spectral densities are plotted across the relevant correlation-time regime to show how motion shapes quadrupolar relaxation.",
    },
    "spin32_algebraic_2004": {
        "b0_b1_energy_map.png": "Transition energies or effective response are mapped as static-field and RF-control scales are varied in the spin-3/2 model.",
        "coherence_order_pathways.png": "The panel resolves which coherence orders are created and mixed by the modeled pulse/evolution sequence in the algebraic representation.",
        "hilbert_vs_liouville_fid.png": "The synthetic FID from direct Hilbert-space evolution is compared with the FID produced by the Liouville-space superoperator implementation.",
        "superoperator_factorization_error.png": "Residual error is quantified when the full Liouville propagator is replaced by the chosen factorized superoperator construction.",
    },
    "qst_relaxation_2008": {
        "density_element_decay.png": "Selected density-matrix elements are followed over time after QST reconstruction to separate population relaxation from coherence decay.",
        "extracted_rate_vs_true.png": "Rates extracted from reconstructed density matrices are compared against the ground-truth synthetic rates used to generate the trajectories.",
        "phase_error_sensitivity.png": "The tomography and fitted-rate output is swept against phase mismatch to reveal how phase calibration biases relaxation identification.",
        "tomography_fidelity_vs_noise.png": "The QST reconstruction fidelity is plotted against increasing synthetic measurement noise.",
    },
    "spin32_qlogic_qst_2005": {
        "all_transition_fidelity_comparison.png": "Selective-pulse performance is compared across the addressed transitions when the internal Hamiltonian is or is not included during the pulse.",
        "population_transfer_vs_duration.png": "Target population transfer is tracked as pulse duration changes, exposing the trade-off between selectivity and unwanted internal evolution.",
        "qst_density_monitor.png": "The reconstructed density matrix after the logical operation is compared with the intended state to expose leakage and phase accumulation.",
        "selective_pulse_fidelity_vs_duration.png": "Logical-operation fidelity is plotted against pulse duration for the idealized pulse model and the full-Hamiltonian pulse model.",
    },
    "nonmarkov_noise_2022": {
        "lindblad_failure_signatures.png": "Residuals and witnesses are combined to show where the Markovian fit fails to reproduce memory-bearing synthetic data.",
        "markovian_vs_memory_ramsey_echo.png": "Synthetic Ramsey and echo decays are contrasted under a memoryless model and a model with effective temporal correlations.",
        "time_local_rate_negative_intervals.png": "The time-local decay rate is plotted to highlight intervals where it becomes negative.",
        "trace_distance_revival.png": "State distinguishability is tracked to reveal revival after an initial loss of information.",
    },
    "multipass_qpt_2024": {
        "error_vs_passes.png": "The mean process-tomography reconstruction error is plotted as the same process is repeated more times before readout.",
        "ptm_comparison.png": "Estimated process matrices are compared with the target process in the Pauli transfer matrix representation.",
        "shot_noise_sweep.png": "Reconstruction performance is swept across different shot counts to measure when multipass QPT becomes worthwhile.",
        "single_vs_multipass_error_distribution.png": "Repeated synthetic trials are summarized as an error distribution for the single-pass and multipass tomography protocols.",
    },
    "quadrupolar_qip_2012": {
        "grover_marked_state_populations.png": "The marked-state population is followed through the encoded Grover-style sequence implemented on the four-level quadrupolar model.",
        "product_operator_decomposition.png": "Spin-3/2 observables are decomposed into the effective two-qubit product-operator language used in quadrupolar NMR QIP.",
        "pseudopure_visibility.png": "The effective contrast or visibility of the pseudo-pure deviation state is monitored after the preparation sequence.",
        "qst_noise_sensitivity.png": "The reconstructed encoded-state fidelity is tracked as synthetic noise is added to the tomography signals.",
    },
    "grape_nmr_control_2005": {
        "grape_fidelity_convergence.png": "The optimization trace records how the target fidelity improves across GRAPE iterations.",
        "optimized_controls.png": "The time-dependent control amplitudes are shown for the pulse that maximizes the spin-3/2 target fidelity.",
        "rectangular_vs_grape_state_fidelity.png": "A direct comparison is made between a simple rectangular pulse and the optimized GRAPE pulse on the same control task.",
        "robustness_map.png": "The optimized pulse is evaluated over a grid of detuning and RF-scale errors to show where high fidelity survives.",
    },
    "pps_optimal_control_2012": {
        "pps_grape_convergence.png": "The optimization history for pseudo-pure-state preparation is plotted as the objective approaches the target deviation state.",
        "pps_optimized_controls.png": "The control amplitudes implementing the pseudo-pure-state preparation are displayed in the optimized time window.",
        "pps_population_profiles.png": "Population or deviation-state components are compared before and after the preparation to show how the target pseudo-pure pattern is created.",
        "pps_qst_noise_sensitivity.png": "The reconstructed pseudo-pure-state fidelity is tracked against increasing synthetic noise in the verification tomography.",
    },
    "projected_ls_qpt_2022": {
        "choi_eigenvalues_raw_vs_pls.png": "The eigenvalues of the reconstructed Choi matrix are shown before and after projection onto the physical CPTP set.",
        "physicality_violations_vs_shots.png": "The frequency or severity of non-CPTP reconstructions is plotted as the measurement shot budget changes.",
        "ptm_reconstruction_comparison.png": "The target PTM is compared with the raw least-squares estimate and the projected least-squares estimate.",
        "qpt_error_distribution.png": "Repeated synthetic trials are summarized as an error distribution for raw and projected process tomography.",
    },
    "gate_set_tomography_2021": {
        "gst_gate_matrix_residuals.png": "The estimated gate matrices are compared with the target predictive model to show where residual structure remains after GST fitting.",
        "gst_gauge_dependent_spam.png": "Preparation and measurement parameters are shown in a way that makes their gauge dependence explicit.",
        "gst_heldout_predictions.png": "The GST model is evaluated on held-out sequence probabilities that were not used directly in the fitting step.",
        "gst_prediction_by_sequence_length.png": "Prediction error is tracked as the calibration sequences become longer and more sensitive to coherent and incoherent gate errors.",
    },
    "nonmarkov_process_tensor_2020": {
        "process_tensor_control_landscape.png": "Candidate controls are scored using a multi-time process-tensor description instead of a memoryless channel.",
        "process_tensor_echo_witness.png": "Multi-time echo observables are compared for the Markovian approximation and the process-tensor model.",
        "process_tensor_prediction_scatter.png": "Predicted versus true observables are scattered for the competing models across the synthetic validation dataset.",
        "process_tensor_rmse_by_length.png": "The root-mean-square prediction error is plotted against the temporal depth of the control/measurement sequence.",
    },
    "noise_filtering_control_2014": {
        "coherence_vs_control_sequence.png": "Ramsey, Hahn, CPMG, and UDD-type sequences are compared through the coherence they preserve under the same synthetic noise spectrum.",
        "filter_peak_tracking.png": "The characteristic filter peak is tracked as the control sequence changes, indicating which spectral band each sequence probes most strongly.",
        "noise_spectrum_and_filters.png": "The synthetic noise spectral density is plotted together with the filter functions of the candidate control sequences.",
        "time_domain_switching_functions.png": "The sign-changing switching functions associated with the control sequences are plotted in the time domain.",
    },
    "dd_noise_spectroscopy_2011": {
        "dd_coherence_fit.png": "Measured synthetic coherences are compared with the coherences predicted after reconstructing the noise spectrum by non-negative least squares.",
        "dd_reconstructed_spectrum.png": "The colored dephasing spectrum inferred from CPMG and UDD data is overlaid with the synthetic ground-truth spectrum.",
        "dd_sequence_sensitivity.png": "The figure shows which frequency regions are emphasized by the DD sequences used in the inversion.",
        "dd_spectrum_residual.png": "The difference between the reconstructed spectrum and the synthetic target spectrum is shown across frequency.",
    },
    "flux_qubit_noise_spectroscopy_2011": {
        "flux_coherence_vs_pulse_count.png": "Synthetic flux-qubit-like coherence is tracked as the number of DD pulses increases and shifts the filter peak through the spectrum.",
        "flux_filter_peak_map.png": "The relation between DD pulse count and the effective peak sensitivity frequency is plotted for the flux-qubit-like benchmark.",
        "flux_power_law_fit.png": "Recovered spectral estimates are fitted to a one-over-f style power law to extract the effective exponent.",
        "flux_spectrum_peak_estimates.png": "Pointwise spectral estimates are extracted by assuming that each DD sequence samples the spectrum near its dominant filter peak.",
    },
    "experimental_decision_pipeline": {
        "control_sequence_decision.png": "Candidate control sequences are ranked by the coherence predicted from the reconstructed spectrum, and the selected sequence is highlighted.",
        "dd_spectroscopy_fit.png": "Measured workflow coherences are compared with the coherences predicted by the spectrum reconstructed from those same measurements.",
        "reconstructed_noise_spectrum.png": "The workflow-level inversion returns an effective noise spectrum that is then used to evaluate candidate control sequences.",
        "state_preparation_qst.png": "The target spin-3/2 state and its tomography reconstruction are compared before the spectroscopy step begins.",
    },
}

FIGURE_TITLE_OVERRIDES: dict[str, str] = {
    "nmr_open_simulation.png": "Open-System Na-23 Simulation Diagnostics",
    "nmr_synthetic_dissipation_fit.png": "Synthetic Dissipation-Fit Validation",
    "nmr_validation_suite.png": "Noise-Robustness Validation Suite",
    "nmr_reference_dissipation_fit.png": "Reference-FID Dissipation Fit",
    "nmr_tomography_pipeline.png": "End-to-End Na-23 Tomography Pipeline",
    "open_qubit_demo.png": "Generic Open-Qubit Demonstration",
    "comparison_figure_count.png": "Artifact Coverage across Reproductions and Workflows",
    "comparison_quality_scores.png": "Normalized Performance Indicators across the Benchmark Suite",
    "comparison_improvement_factors.png": "Improvement Factors Relative to Each Baseline Protocol",
    "comparison_error_metrics.png": "Representative Residual and Error Metrics across Benchmarks",
    "internal_validation_baseline.png": "Spin-3/2 Baseline Validation Panel",
    "envelope_residuals.png": "Residual Comparison of Relaxation-Envelope Models",
    "phenomenological_vs_redfield_decay.png": "Phenomenological versus Redfield-Inspired Relaxation",
    "rates_vs_tau_c.png": "Relaxation Rates versus Correlation Time",
    "spectral_density_regimes.png": "Reduced Spectral-Density Regimes",
    "b0_b1_energy_map.png": "B0/B1 Energy and Sensitivity Map",
    "coherence_order_pathways.png": "Coherence-Order Pathways in the Spin-3/2 Algebra",
    "hilbert_vs_liouville_fid.png": "Hilbert- versus Liouville-Space FID Comparison",
    "superoperator_factorization_error.png": "Superoperator-Factorization Error",
    "density_element_decay.png": "Density-Matrix Element Decay under QST",
    "extracted_rate_vs_true.png": "Extracted versus True Relaxation Rates",
    "phase_error_sensitivity.png": "Sensitivity to Tomography Phase Error",
    "tomography_fidelity_vs_noise.png": "QST Fidelity versus Measurement Noise",
    "all_transition_fidelity_comparison.png": "Selective-Pulse Fidelity across Addressed Transitions",
    "population_transfer_vs_duration.png": "Population Transfer versus Pulse Duration",
    "qst_density_monitor.png": "QST Density-Matrix Monitor after Logical Operation",
    "selective_pulse_fidelity_vs_duration.png": "Selective-Pulse Fidelity versus Duration",
    "lindblad_failure_signatures.png": "Failure Signatures of the Markovian Fit",
    "markovian_vs_memory_ramsey_echo.png": "Ramsey and Echo Decay: Markovian versus Memory Models",
    "time_local_rate_negative_intervals.png": "Negative Intervals of the Time-Local Rate",
    "trace_distance_revival.png": "Trace-Distance Revival under Non-Markovian Dynamics",
    "error_vs_passes.png": "Process-Tomography Error versus Number of Passes",
    "ptm_comparison.png": "PTM Reconstruction Comparison",
    "shot_noise_sweep.png": "Shot-Noise Dependence of Multipass QPT",
    "single_vs_multipass_error_distribution.png": "Error Distribution: Single-Pass versus Multipass QPT",
    "grover_marked_state_populations.png": "Marked-State Population in Encoded Grover Dynamics",
    "product_operator_decomposition.png": "Encoded Two-Qubit Product-Operator Decomposition",
    "pseudopure_visibility.png": "Pseudo-Pure-State Visibility",
    "qst_noise_sensitivity.png": "QST Robustness to Measurement Noise",
    "grape_fidelity_convergence.png": "GRAPE Fidelity Convergence",
    "optimized_controls.png": "Optimized Control Waveforms",
    "rectangular_vs_grape_state_fidelity.png": "State Fidelity: Rectangular versus GRAPE Control",
    "robustness_map.png": "Robustness Map over Detuning and RF Scale",
    "pps_grape_convergence.png": "GRAPE Convergence for Pseudo-Pure-State Preparation",
    "pps_optimized_controls.png": "Optimized Controls for Pseudo-Pure-State Preparation",
    "pps_population_profiles.png": "Population Profiles for Pseudo-Pure-State Preparation",
    "pps_qst_noise_sensitivity.png": "Pseudo-Pure-State QST Robustness to Noise",
    "choi_eigenvalues_raw_vs_pls.png": "Choi Eigenvalues: Raw versus Projected Least Squares",
    "physicality_violations_vs_shots.png": "Physicality Violations versus Shot Count",
    "ptm_reconstruction_comparison.png": "PTM Reconstruction: Raw versus Projected Estimators",
    "qpt_error_distribution.png": "Quantum Process Tomography Error Distribution",
    "gst_gate_matrix_residuals.png": "Gate-Matrix Residuals after GST Fitting",
    "gst_gauge_dependent_spam.png": "Gauge-Dependent SPAM Parameters in GST",
    "gst_heldout_predictions.png": "Held-Out Predictive Performance of GST",
    "gst_prediction_by_sequence_length.png": "GST Prediction Error versus Sequence Length",
    "process_tensor_control_landscape.png": "Control Landscape under the Process-Tensor Model",
    "process_tensor_echo_witness.png": "Echo Witness: Process Tensor versus Markovian Channel",
    "process_tensor_prediction_scatter.png": "Predicted versus True Observables under Competing Models",
    "process_tensor_rmse_by_length.png": "Prediction RMSE versus Sequence Temporal Depth",
    "coherence_vs_control_sequence.png": "Coherence versus Control Sequence Family",
    "filter_peak_tracking.png": "Tracking the Dominant Filter Peak",
    "noise_spectrum_and_filters.png": "Noise Spectrum and Control-Sequence Filters",
    "time_domain_switching_functions.png": "Time-Domain Switching Functions",
    "dd_coherence_fit.png": "DD Coherence Fit after Spectral Reconstruction",
    "dd_reconstructed_spectrum.png": "Dynamical-Decoupling Reconstructed Spectrum",
    "dd_sequence_sensitivity.png": "Frequency Sensitivity of the DD Sequence Set",
    "dd_spectrum_residual.png": "Residual Spectrum after DD Reconstruction",
    "flux_coherence_vs_pulse_count.png": "Flux-Qubit Coherence versus Pulse Count",
    "flux_filter_peak_map.png": "Filter-Peak Map for Flux-Qubit Spectroscopy",
    "flux_power_law_fit.png": "Power-Law Fit to the Recovered Noise Spectrum",
    "flux_spectrum_peak_estimates.png": "Peak-Based Spectral Estimates for the Flux-Qubit Benchmark",
    "control_sequence_decision.png": "Control-Sequence Decision from Reconstructed Noise",
    "dd_spectroscopy_fit.png": "Workflow DD Spectroscopy Fit",
    "reconstructed_noise_spectrum.png": "Reconstructed Effective Noise Spectrum",
    "state_preparation_qst.png": "State Preparation and QST Validation",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_state() -> dict[str, dict[str, str]]:
    if not ANNOTATION_STATE_PATH.exists():
        return {}
    return json.loads(ANNOTATION_STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict[str, dict[str, str]]) -> None:
    ANNOTATION_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def humanize_figure_name(filename: str) -> str:
    if filename in FIGURE_TITLE_OVERRIDES:
        return FIGURE_TITLE_OVERRIDES[filename]

    replacements = {
        "qst": "QST",
        "dd": "DD",
        "grape": "GRAPE",
        "ptm": "PTM",
        "pps": "PPS",
        "fid": "FID",
        "rmse": "RMSE",
        "spam": "SPAM",
        "raw": "Raw",
        "pls": "PLS",
        "cptp": "CPTP",
        "choi": "Choi",
        "b0": "B0",
        "b1": "B1",
        "tau": "Tau",
    }
    words: list[str] = []
    for token in filename.replace(".png", "").split("_"):
        low = token.lower()
        if low == "vs":
            words.append("versus")
        elif low in replacements:
            words.append(replacements[low])
        else:
            words.append(token.capitalize())
    return " ".join(words).strip()


def reference_for_source(source_id: str) -> str:
    return SOURCE_REFERENCES.get(source_id, "Internal repository reference.")


def role_for_source(source_id: str) -> str:
    return SOURCE_ROLES.get(source_id, "support the internal reproducibility layer")


def output_figure_note(source_id: str, filename: str, summary: str) -> dict[str, str]:
    return {
        "title": humanize_figure_name(filename),
        "summary": summary,
        "interpretation": f"In this laboratory, the figure is used to {role_for_source(source_id)}. It should be read together with the matching metrics.json and results.json files, because visual agreement alone is not treated as sufficient evidence.",
        "reference": reference_for_source(source_id),
    }


def summary_for_output_figure(source_id: str, filename: str) -> str:
    return OUTPUT_FIGURE_SUMMARIES.get(source_id, {}).get(
        filename,
        "This generated plot belongs to the current reproduction and should be read together with the matching metrics and configuration files.",
    )


def base_figure_note(filename: str) -> dict[str, str]:
    summary = BASE_FIGURE_NOTES.get(
        filename,
        "This base laboratory plot records a platform-level simulation or validation result.",
    )
    return {
        "title": humanize_figure_name(filename),
        "summary": summary,
        "interpretation": "This is a foundational artifact for the repository rather than a standalone external-paper result. It defines what is numerically and physically trusted before new experiments are interpreted.",
        "reference": "Internal laboratory base artifact.",
    }


def comparison_figure_note(filename: str) -> dict[str, str]:
    summary = COMPARISON_FIGURE_NOTES.get(
        filename,
        "This comparison figure aggregates information across multiple reproductions or workflows.",
    )
    return {
        "title": humanize_figure_name(filename),
        "summary": summary,
        "interpretation": "The purpose is structural comparison across the laboratory stack. The numbers are heterogeneous and are not meant to rank distinct physical observables as if they were the same quantity.",
        "reference": "Internal synthesis across the full paper-reproduction and workflow layer.",
    }


def markdown_figure_block(relative_image_path: str, note: dict[str, str], index: int) -> list[str]:
    return [
        f"### Figure {index}. {note['title']}",
        "",
        f"![{note['title']}]({relative_image_path})",
        "",
        f"- Summary: {note['summary']}",
        f"- Interpretation: {note['interpretation']}",
        f"- Reference: {note['reference']}",
        "",
    ]


def latex_caption_from_note(note: dict[str, str]) -> str:
    return " ".join(
        [
            f"{note['title']}.",
            note["summary"],
            note["interpretation"],
            f"Reference: {note['reference']}",
        ]
    )


def annotation_lines_from_note(note: dict[str, str]) -> list[str]:
    return [
        f"Title: {note['title']}",
        f"Summary: {note['summary']}",
        f"Interpretation: {note['interpretation']}",
        f"Reference: {note['reference']}",
    ]


def _render_annotation(path: Path, lines: list[str]) -> None:
    last_error: Exception | None = None
    image = None
    for _ in range(3):
        try:
            image = plt.imread(path)
            break
        except (OSError, SyntaxError) as exc:
            last_error = exc
            time.sleep(0.2)
    if image is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Could not load image for annotation: {path}")
    height, width = image.shape[0], image.shape[1]
    aspect = width / max(height, 1)
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(textwrap.wrap(line, width=118, break_long_words=False, break_on_hyphens=False))
    image_height = 10.0 / max(aspect, 0.35)
    caption_height = max(2.0, 0.34 * len(wrapped_lines))

    fig = plt.figure(figsize=(10.0, image_height + caption_height))
    gs = fig.add_gridspec(2, 1, height_ratios=[image_height, caption_height], hspace=0.02)
    ax_image = fig.add_subplot(gs[0])
    ax_image.imshow(image)
    ax_image.axis("off")

    ax_text = fig.add_subplot(gs[1])
    ax_text.axis("off")
    ax_text.add_patch(
        patches.Rectangle(
            (0.0, 0.0),
            1.0,
            1.0,
            transform=ax_text.transAxes,
            facecolor="#f4f4f4",
            edgecolor="#d0d0d0",
            linewidth=1.0,
        )
    )
    ax_text.text(0.02, 0.96, "\n".join(wrapped_lines), va="top", ha="left", fontsize=9.2, family="DejaVu Serif")
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def annotate_tracked_png(path: Path, note: dict[str, str]) -> bool:
    if not path.exists():
        return False
    state = _load_state()
    relative = path.relative_to(ROOT).as_posix()
    current_hash = _sha256_file(path)
    caption_hash = hashlib.sha256(json.dumps(note, sort_keys=True).encode("utf-8")).hexdigest()
    record = state.get(relative)
    if record and record.get("file_hash") == current_hash and record.get("caption_hash") == caption_hash:
        return False
    _render_annotation(path, annotation_lines_from_note(note))
    state[relative] = {"caption_hash": caption_hash, "file_hash": _sha256_file(path)}
    _save_state(state)
    return True


def annotate_untracked_png(path: Path, note: dict[str, str]) -> bool:
    if not path.exists():
        return False
    _render_annotation(path, annotation_lines_from_note(note))
    return True


def annotate_output_directory(source_id: str, output_dir: Path) -> int:
    count = 0
    for png in sorted(output_dir.rglob("*.png")):
        note = output_figure_note(source_id, png.name, summary_for_output_figure(source_id, png.name))
        count += int(annotate_tracked_png(png, note))
    return count


def annotate_base_figures() -> int:
    count = 0
    for png in sorted((ROOT / "outputs").glob("*.png")):
        count += int(annotate_tracked_png(png, base_figure_note(png.name)))
    return count


def clean_results_payload(results_path: Path) -> bool:
    if not results_path.exists():
        return False
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    changed = False
    for key in ("markdown_note", "report_file"):
        if key in payload:
            payload.pop(key)
            changed = True
    if changed:
        results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return changed


def remove_redundant_markdown(output_dir: Path) -> int:
    removed = 0
    for name in ("reproduction_note.md", "workflow_report.md", "comparison_report_template.md"):
        path = output_dir / name
        if path.exists():
            path.unlink()
            removed += 1
    return removed


def collect_annotation_summary() -> dict[str, Any]:
    state = _load_state()
    return {"tracked_entries": len(state), "state_file": str(ANNOTATION_STATE_PATH)}
