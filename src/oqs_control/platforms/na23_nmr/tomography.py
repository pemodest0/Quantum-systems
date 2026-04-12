from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import sqrtm

from .config import NMRConfig


@dataclass(frozen=True)
class TomographyResult:
    signals: np.ndarray
    reconstructed_rho: np.ndarray
    residual_norm: float
    trace_value: complex
    phases_rad: np.ndarray
    fidelity: float | None = None
    frobenius_error: float | None = None


def matrix_unit(dim: int, row: int, col: int) -> np.ndarray:
    out = np.zeros((dim, dim), dtype=complex)
    out[row, col] = 1.0
    return out


def tomography_phases(config: NMRConfig) -> np.ndarray:
    return np.arange(7, dtype=float) * 2.0 * np.pi / 7.0


def simulate_tomography_signals(rho: np.ndarray, config: NMRConfig) -> np.ndarray:
    signals = np.zeros((7, len(config.transition_pairs)), dtype=complex)
    for phase_idx in range(7):
        u_phase = config.u_tomop[:, :, phase_idx]
        rotated = u_phase @ rho @ u_phase.conj().T
        for pair_idx, (i, j) in enumerate(config.transition_pairs):
            signals[phase_idx, pair_idx] = rotated[i, j]
    return signals


def _build_linear_system(
    config: NMRConfig, signals: np.ndarray, trace_weight: float
) -> tuple[np.ndarray, np.ndarray]:
    rows: list[np.ndarray] = []
    values: list[complex] = []

    for phase_idx in range(7):
        u_phase = config.u_tomop[:, :, phase_idx]
        for pair_idx, (i, j) in enumerate(config.transition_pairs):
            e_ji = matrix_unit(config.dim, j, i)
            measurement = u_phase.conj().T @ e_ji @ u_phase
            rows.append(measurement.T.reshape(-1))
            values.append(signals[phase_idx, pair_idx])

    rows.append(trace_weight * np.eye(config.dim, dtype=complex).T.reshape(-1))
    values.append(trace_weight * 1.0)
    return np.vstack(rows), np.array(values, dtype=complex)


def project_density_matrix(rho: np.ndarray, enforce_psd: bool = True) -> np.ndarray:
    hermitian = 0.5 * (rho + rho.conj().T)
    trace = np.trace(hermitian)
    if trace == 0:
        hermitian = hermitian + np.eye(hermitian.shape[0], dtype=complex) / hermitian.shape[0]
        trace = np.trace(hermitian)
    hermitian = hermitian / trace

    if not enforce_psd:
        return hermitian

    evals, evecs = np.linalg.eigh(hermitian)
    evals = np.clip(evals.real, 0.0, None)
    if np.sum(evals) == 0:
        evals[:] = 1.0 / evals.size
    projected = evecs @ np.diag(evals / np.sum(evals)) @ evecs.conj().T
    return projected


def reconstruct_density_matrix(
    signals: np.ndarray,
    config: NMRConfig,
    trace_weight: float = 10.0,
    enforce_psd: bool = True,
    rho_true: np.ndarray | None = None,
) -> TomographyResult:
    a_mat, b_vec = _build_linear_system(config, signals, trace_weight)
    x_vec, *_ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
    rho_raw = x_vec.reshape(config.dim, config.dim)
    rho_rec = project_density_matrix(rho_raw, enforce_psd=enforce_psd)

    residual = a_mat @ rho_rec.reshape(-1) - b_vec
    fidelity = None
    frobenius_error = None
    if rho_true is not None:
        fidelity = state_fidelity(rho_true, rho_rec)
        frobenius_error = float(np.linalg.norm(rho_true - rho_rec))

    return TomographyResult(
        signals=np.array(signals, copy=True),
        reconstructed_rho=rho_rec,
        residual_norm=float(np.linalg.norm(residual)),
        trace_value=complex(np.trace(rho_rec)),
        phases_rad=tomography_phases(config),
        fidelity=fidelity,
        frobenius_error=frobenius_error,
    )


def state_fidelity(rho_a: np.ndarray, rho_b: np.ndarray) -> float:
    sqrt_a = sqrtm(rho_a)
    inner = sqrt_a @ rho_b @ sqrt_a
    fidelity = np.trace(sqrtm(inner)) ** 2
    return float(np.clip(np.real_if_close(fidelity).real, 0.0, 1.0))
