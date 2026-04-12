from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..open_systems.noise_filtering import (
    PulseSequence,
    cpmg_sequence,
    filter_peak_frequency,
    hahn_echo_sequence,
    ramsey_sequence,
    udd_sequence,
)
from ..open_systems.noise_spectroscopy import (
    SpectrumReconstruction,
    add_coherence_noise,
    colored_noise_spectrum,
    reconstruct_spectrum_nnls,
    simulate_coherences,
)
from ..platforms.na23_nmr.config import NMRConfig
from ..platforms.na23_nmr.qst_relaxation import (
    add_tomography_noise,
    coherent_superposition_state,
    mix_with_identity,
)
from ..platforms.na23_nmr.tomography import (
    TomographyResult,
    reconstruct_density_matrix,
    simulate_tomography_signals,
)


WORKFLOW_ID = "experimental_decision_pipeline"


@dataclass(frozen=True)
class ExperimentalDecisionConfig:
    """Configuration for the synthetic experimental decision workflow."""

    total_time_s: float = 1.2e-3
    frequency_min_hz: float = 200.0
    frequency_max_hz: float = 16.0e3
    frequency_points: int = 180
    spectroscopy_cpmg_min: int = 1
    spectroscopy_cpmg_max: int = 24
    spectroscopy_udd_counts: tuple[int, ...] = (2, 4, 6, 8, 10, 12)
    candidate_cpmg_counts: tuple[int, ...] = (2, 4, 8, 12, 16, 24, 32)
    candidate_udd_counts: tuple[int, ...] = (4, 8, 12, 16)
    coherence_noise_std: float = 0.003
    qst_noise_std: float = 0.01
    qst_phase_error_rad: float = 0.006
    nnls_smoothness: float = 1.0e-3
    n_time_samples: int = 768
    random_seed: int = 20260411


@dataclass(frozen=True)
class StatePreparationDecision:
    target_state: np.ndarray
    reconstructed_state: np.ndarray
    fidelity: float
    frobenius_error: float
    tomography_residual_norm: float
    prepared_coherence_norm: float


@dataclass(frozen=True)
class ControlSequenceDecision:
    sequence: str
    pulse_count: int
    filter_peak_hz: float
    predicted_coherence: float
    synthetic_true_coherence: float
    prediction_error: float


@dataclass(frozen=True)
class LabComparison:
    status: str
    matched_measurement_count: int
    rmse: float | None
    normalized_rmse: float | None
    residuals: tuple[dict[str, float | str], ...]


@dataclass(frozen=True)
class ExperimentalDecisionResult:
    workflow_id: str
    config: ExperimentalDecisionConfig
    state_preparation: StatePreparationDecision
    omega_rad_s: np.ndarray
    true_spectrum: np.ndarray
    reconstruction: SpectrumReconstruction
    spectroscopy_sequences: tuple[PulseSequence, ...]
    measured_coherence: np.ndarray
    candidate_decisions: tuple[ControlSequenceDecision, ...]
    selected_sequence: ControlSequenceDecision
    lab_comparison: LabComparison


def config_to_json_dict(config: ExperimentalDecisionConfig) -> dict[str, Any]:
    payload = asdict(config)
    for key, value in list(payload.items()):
        if isinstance(value, tuple):
            payload[key] = list(value)
    return payload


def default_spectroscopy_sequences(config: ExperimentalDecisionConfig) -> tuple[PulseSequence, ...]:
    cpmg = tuple(
        cpmg_sequence(config.total_time_s, count)
        for count in range(config.spectroscopy_cpmg_min, config.spectroscopy_cpmg_max + 1)
    )
    udd = tuple(udd_sequence(config.total_time_s, count) for count in config.spectroscopy_udd_counts)
    return cpmg + udd


def default_candidate_sequences(config: ExperimentalDecisionConfig) -> tuple[PulseSequence, ...]:
    candidates = [ramsey_sequence(config.total_time_s), hahn_echo_sequence(config.total_time_s)]
    candidates.extend(cpmg_sequence(config.total_time_s, count) for count in config.candidate_cpmg_counts)
    candidates.extend(udd_sequence(config.total_time_s, count) for count in config.candidate_udd_counts)
    return tuple(candidates)


def default_frequency_grid(config: ExperimentalDecisionConfig) -> np.ndarray:
    return np.linspace(
        2.0 * np.pi * config.frequency_min_hz,
        2.0 * np.pi * config.frequency_max_hz,
        int(config.frequency_points),
    )


def prepare_and_tomograph_reference_state(
    nmr_config: NMRConfig,
    config: ExperimentalDecisionConfig,
) -> StatePreparationDecision:
    rng = np.random.default_rng(config.random_seed + 17)
    target_state = mix_with_identity(coherent_superposition_state(nmr_config.dim), mixing=0.04)
    clean_signals = simulate_tomography_signals(target_state, nmr_config)
    measured_signals = add_tomography_noise(
        clean_signals,
        noise_std=config.qst_noise_std,
        rng=rng,
        phase_error_rad=config.qst_phase_error_rad,
    )
    qst_result: TomographyResult = reconstruct_density_matrix(
        measured_signals,
        nmr_config,
        enforce_psd=True,
        rho_true=target_state,
    )
    reconstructed = qst_result.reconstructed_rho
    offdiag = reconstructed - np.diag(np.diag(reconstructed))
    return StatePreparationDecision(
        target_state=target_state,
        reconstructed_state=reconstructed,
        fidelity=float(qst_result.fidelity if qst_result.fidelity is not None else np.nan),
        frobenius_error=float(qst_result.frobenius_error if qst_result.frobenius_error is not None else np.nan),
        tomography_residual_norm=float(qst_result.residual_norm),
        prepared_coherence_norm=float(np.linalg.norm(offdiag)),
    )


def synthetic_noise_spectrum(omega_rad_s: np.ndarray) -> np.ndarray:
    return colored_noise_spectrum(
        omega_rad_s,
        amplitude=60.0,
        peak_amplitude=42.0,
        white_floor=0.03,
        peak_center_hz=6.0e3,
        peak_width_hz=0.8e3,
    )


def score_control_sequences(
    omega_rad_s: np.ndarray,
    reconstructed_spectrum: np.ndarray,
    true_spectrum: np.ndarray,
    sequences: tuple[PulseSequence, ...],
    n_time_samples: int,
) -> tuple[ControlSequenceDecision, ...]:
    predicted_coherence, _ = simulate_coherences(
        omega_rad_s,
        reconstructed_spectrum,
        sequences,
        n_time_samples=n_time_samples,
    )
    true_coherence, _ = simulate_coherences(
        omega_rad_s,
        true_spectrum,
        sequences,
        n_time_samples=n_time_samples,
    )

    rows: list[ControlSequenceDecision] = []
    for sequence, predicted, true_value in zip(sequences, predicted_coherence, true_coherence):
        rows.append(
            ControlSequenceDecision(
                sequence=sequence.name,
                pulse_count=int(len(sequence.pulse_times_s)),
                filter_peak_hz=float(
                    filter_peak_frequency(
                        omega_rad_s,
                        sequence,
                        n_time_samples=n_time_samples,
                    )
                    / (2.0 * np.pi)
                ),
                predicted_coherence=float(predicted),
                synthetic_true_coherence=float(true_value),
                prediction_error=float(predicted - true_value),
            )
        )
    return tuple(rows)


def select_control_sequence(decisions: tuple[ControlSequenceDecision, ...]) -> ControlSequenceDecision:
    if not decisions:
        raise ValueError("at least one candidate sequence is required")
    return max(decisions, key=lambda row: (row.predicted_coherence, -row.pulse_count))


def load_lab_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"lab manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compare_lab_data(
    decisions: tuple[ControlSequenceDecision, ...],
    lab_manifest: dict[str, Any] | None,
) -> LabComparison:
    if lab_manifest is None:
        return LabComparison(
            status="waiting_for_lab_data",
            matched_measurement_count=0,
            rmse=None,
            normalized_rmse=None,
            residuals=(),
        )

    by_name = {decision.sequence: decision for decision in decisions}
    residuals: list[dict[str, float | str]] = []
    normalized_values: list[float] = []
    raw_values: list[float] = []
    for measurement in lab_manifest.get("coherence_measurements", []):
        sequence = str(measurement.get("sequence", ""))
        if sequence not in by_name:
            continue
        measured = float(measurement["coherence"])
        sigma = float(measurement.get("std", np.nan))
        predicted = by_name[sequence].predicted_coherence
        residual = predicted - measured
        raw_values.append(residual)
        row: dict[str, float | str] = {
            "sequence": sequence,
            "measured_coherence": measured,
            "predicted_coherence": predicted,
            "residual": residual,
        }
        if np.isfinite(sigma) and sigma > 0.0:
            row["std"] = sigma
            row["normalized_residual"] = residual / sigma
            normalized_values.append(residual / sigma)
        residuals.append(row)

    if not raw_values:
        return LabComparison(
            status="no_matching_lab_sequences",
            matched_measurement_count=0,
            rmse=None,
            normalized_rmse=None,
            residuals=(),
        )

    return LabComparison(
        status="compared",
        matched_measurement_count=len(raw_values),
        rmse=float(np.sqrt(np.mean(np.square(raw_values)))),
        normalized_rmse=float(np.sqrt(np.mean(np.square(normalized_values)))) if normalized_values else None,
        residuals=tuple(residuals),
    )


def run_pipeline(
    config: ExperimentalDecisionConfig | None = None,
    lab_manifest_path: Path | None = None,
    nmr_config: NMRConfig | None = None,
) -> ExperimentalDecisionResult:
    active_config = config or ExperimentalDecisionConfig()
    active_nmr_config = nmr_config or NMRConfig(n_acq=256, n_zf=256)
    state_preparation = prepare_and_tomograph_reference_state(active_nmr_config, active_config)

    omega = default_frequency_grid(active_config)
    true_spectrum = synthetic_noise_spectrum(omega)
    spectroscopy_sequences = default_spectroscopy_sequences(active_config)
    clean_coherence, _ = simulate_coherences(
        omega,
        true_spectrum,
        spectroscopy_sequences,
        n_time_samples=active_config.n_time_samples,
    )
    measured_coherence = add_coherence_noise(
        clean_coherence,
        noise_std=active_config.coherence_noise_std,
        seed=active_config.random_seed,
    )
    reconstruction = reconstruct_spectrum_nnls(
        omega,
        spectroscopy_sequences,
        measured_coherence,
        smoothness=active_config.nnls_smoothness,
        n_time_samples=active_config.n_time_samples,
        true_spectrum=true_spectrum,
    )

    decisions = score_control_sequences(
        omega,
        reconstruction.reconstructed_spectrum,
        true_spectrum,
        default_candidate_sequences(active_config),
        n_time_samples=active_config.n_time_samples,
    )
    selected = select_control_sequence(decisions)
    comparison = compare_lab_data(decisions, load_lab_manifest(lab_manifest_path))
    return ExperimentalDecisionResult(
        workflow_id=WORKFLOW_ID,
        config=active_config,
        state_preparation=state_preparation,
        omega_rad_s=omega,
        true_spectrum=true_spectrum,
        reconstruction=reconstruction,
        spectroscopy_sequences=spectroscopy_sequences,
        measured_coherence=measured_coherence,
        candidate_decisions=decisions,
        selected_sequence=selected,
        lab_comparison=comparison,
    )


def decisions_to_json(decisions: tuple[ControlSequenceDecision, ...]) -> list[dict[str, float | int | str]]:
    return [asdict(decision) for decision in decisions]


def lab_manifest_template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": "replace_with_lab_run_id",
        "platform": "23Na quadrupolar NMR or gate-model hardware",
        "sample_or_device": "replace_with_sample_or_device_id",
        "acquired_at_utc": None,
        "operator": None,
        "notes": "Populate coherence_measurements after the lab run.",
        "coherence_measurements": [
            {"sequence": "CPMG-8", "coherence": None, "std": None, "shots_or_scans": None},
            {"sequence": "CPMG-16", "coherence": None, "std": None, "shots_or_scans": None},
            {"sequence": "UDD-8", "coherence": None, "std": None, "shots_or_scans": None},
        ],
        "qst_summary": {
            "state_label": None,
            "density_matrix_file": None,
            "reconstruction_fidelity": None,
            "tomography_residual_norm": None,
        },
    }


def comparison_report_template() -> str:
    return "\n".join(
        [
            "# Experimental Comparison Report",
            "",
            "Use this template after real data arrive.",
            "",
            "## Input Manifest",
            "",
            "- Experiment ID:",
            "- Platform:",
            "- Sample or device:",
            "- Acquisition date:",
            "",
            "## Model Snapshot",
            "",
            "- Pipeline run directory:",
            "- Config hash:",
            "- Selected control sequence:",
            "- Reconstructed spectrum summary:",
            "",
            "## Agreement Checks",
            "",
            "- Coherence RMSE:",
            "- Normalized RMSE:",
            "- Largest residual sequence:",
            "- QST consistency notes:",
            "",
            "## Decision",
            "",
            "- Accept current model:",
            "- Refit spectrum:",
            "- Add pulse-error model:",
            "- Add non-Markovian memory model:",
            "",
        ]
    )
