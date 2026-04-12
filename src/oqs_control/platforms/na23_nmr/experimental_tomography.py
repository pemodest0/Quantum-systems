from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from .analysis import (
    TransitionAmplitudeEstimate,
    extract_transition_amplitudes,
    flatten_first_trace,
)
from .config import NMRConfig
from .io import read_tnt
from .simulation import simulate_fid
from .tomography import project_density_matrix, state_fidelity


@dataclass(frozen=True)
class ExtractionSettings:
    zero_fill_factor: int = 4
    line_broadening_hz: float = 0.0
    integration_window_hz: float = 800.0
    diagnostic_search_hz: float = 1500.0


@dataclass(frozen=True)
class PhaseMeasurement:
    phase_index: int
    phase_rad: float
    path: str | None
    estimates: tuple[TransitionAmplitudeEstimate, ...]


@dataclass(frozen=True)
class ExperimentalTomographyRun:
    signals: np.ndarray
    reconstructed_rho: np.ndarray
    residual_norm: float
    trace_value: complex
    phase_measurements: tuple[PhaseMeasurement, ...]
    fidelity: float | None = None
    frobenius_error: float | None = None


def _measurement_vector(signals: np.ndarray) -> np.ndarray:
    return np.asarray(signals, dtype=complex).reshape(-1)


def extract_measurement_from_fid(
    fid: np.ndarray,
    phase_index: int,
    config: NMRConfig,
    settings: ExtractionSettings | None = None,
    path: str | None = None,
) -> PhaseMeasurement:
    active = settings or ExtractionSettings()
    _, _, estimates = extract_transition_amplitudes(
        signal=fid,
        dwell_time=config.dwell_time,
        centers_hz=config.expected_transition_centers_hz,
        labels=config.transition_labels,
        zero_fill_factor=active.zero_fill_factor,
        line_broadening_hz=active.line_broadening_hz,
        integration_window_hz=active.integration_window_hz,
        diagnostic_search_hz=active.diagnostic_search_hz,
    )
    return PhaseMeasurement(
        phase_index=int(phase_index),
        phase_rad=float(phase_index * 2.0 * np.pi / 7.0),
        path=path,
        estimates=tuple(estimates),
    )


def signals_from_phase_measurements(
    measurements: list[PhaseMeasurement] | tuple[PhaseMeasurement, ...]
) -> np.ndarray:
    if len(measurements) != 7:
        raise ValueError("Tomography phase series must contain exactly 7 measurements")
    ordered = sorted(measurements, key=lambda item: item.phase_index)
    if [m.phase_index for m in ordered] != list(range(7)):
        raise ValueError("Phase indices must cover 0..6 exactly once")
    return np.array(
        [[estimate.complex_amplitude for estimate in m.estimates] for m in ordered],
        dtype=complex,
    )


def build_measurement_matrix(
    config: NMRConfig, settings: ExtractionSettings | None = None
) -> np.ndarray:
    active = settings or ExtractionSettings()
    dim = config.dim
    a_mat = np.zeros((7 * len(config.transition_labels), dim * dim), dtype=complex)

    for row in range(dim):
        for col in range(dim):
            basis = np.zeros((dim, dim), dtype=complex)
            basis[row, col] = 1.0
            measurements: list[PhaseMeasurement] = []
            for phase_index in range(7):
                rho_phase = (
                    config.u_tomop[:, :, phase_index]
                    @ basis
                    @ config.u_tomop[:, :, phase_index].conj().T
                )
                fid = simulate_fid(config, rho0=rho_phase)
                measurements.append(
                    extract_measurement_from_fid(
                        fid=fid,
                        phase_index=phase_index,
                        config=config,
                        settings=active,
                    )
                )
            a_mat[:, row * dim + col] = _measurement_vector(
                signals_from_phase_measurements(measurements)
            )

    return a_mat


def reconstruct_from_signal_matrix(
    signals: np.ndarray,
    config: NMRConfig,
    settings: ExtractionSettings | None = None,
    trace_weight: float = 10.0,
    enforce_psd: bool = True,
    rho_true: np.ndarray | None = None,
    phase_measurements: list[PhaseMeasurement] | tuple[PhaseMeasurement, ...] | None = None,
) -> ExperimentalTomographyRun:
    a_meas = build_measurement_matrix(config, settings=settings)
    b_meas = _measurement_vector(signals)
    trace_row = trace_weight * np.eye(config.dim, dtype=complex).T.reshape(-1)
    a_full = np.vstack([a_meas, trace_row])
    b_full = np.concatenate([b_meas, np.array([trace_weight], dtype=complex)])

    x_vec, *_ = np.linalg.lstsq(a_full, b_full, rcond=None)
    rho_raw = x_vec.reshape(config.dim, config.dim)
    rho_rec = project_density_matrix(rho_raw, enforce_psd=enforce_psd)

    residual = a_full @ rho_rec.reshape(-1) - b_full
    fidelity = None
    frobenius_error = None
    if rho_true is not None:
        fidelity = state_fidelity(rho_true, rho_rec)
        frobenius_error = float(np.linalg.norm(rho_true - rho_rec))

    ordered_measurements = (
        tuple(sorted(phase_measurements, key=lambda item: item.phase_index))
        if phase_measurements
        else tuple()
    )
    return ExperimentalTomographyRun(
        signals=np.array(signals, copy=True),
        reconstructed_rho=rho_rec,
        residual_norm=float(np.linalg.norm(residual)),
        trace_value=complex(np.trace(rho_rec)),
        phase_measurements=ordered_measurements,
        fidelity=fidelity,
        frobenius_error=frobenius_error,
    )


def simulate_experimental_phase_series(
    rho: np.ndarray,
    config: NMRConfig,
    settings: ExtractionSettings | None = None,
) -> tuple[PhaseMeasurement, ...]:
    measurements: list[PhaseMeasurement] = []
    for phase_index in range(7):
        rho_phase = (
            config.u_tomop[:, :, phase_index]
            @ rho
            @ config.u_tomop[:, :, phase_index].conj().T
        )
        fid = simulate_fid(config, rho0=rho_phase)
        measurements.append(
            extract_measurement_from_fid(
                fid=fid,
                phase_index=phase_index,
                config=config,
                settings=settings,
            )
        )
    return tuple(measurements)


def reconstruct_from_simulated_phase_series(
    rho: np.ndarray,
    config: NMRConfig,
    settings: ExtractionSettings | None = None,
) -> ExperimentalTomographyRun:
    measurements = simulate_experimental_phase_series(rho, config, settings=settings)
    signals = signals_from_phase_measurements(measurements)
    return reconstruct_from_signal_matrix(
        signals=signals,
        config=config,
        settings=settings,
        rho_true=rho,
        phase_measurements=measurements,
    )


def load_phase_manifest(path: str | Path) -> list[dict[str, object]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    phase_files = data.get("phase_files")
    if not isinstance(phase_files, list):
        raise ValueError("Manifest must contain a 'phase_files' list")
    return phase_files


def reconstruct_from_manifest(
    manifest_path: str | Path,
    config: NMRConfig,
    settings: ExtractionSettings | None = None,
) -> ExperimentalTomographyRun:
    active = settings or ExtractionSettings()
    measurements: list[PhaseMeasurement] = []
    for entry in load_phase_manifest(manifest_path):
        phase_index = int(entry["phase_index"])
        path = str(entry["path"])
        fid = flatten_first_trace(read_tnt(path))
        measurements.append(
            extract_measurement_from_fid(
                fid=fid,
                phase_index=phase_index,
                config=config,
                settings=active,
                path=path,
            )
        )
    signals = signals_from_phase_measurements(measurements)
    return reconstruct_from_signal_matrix(
        signals=signals,
        config=config,
        settings=active,
        phase_measurements=measurements,
    )
