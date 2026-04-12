from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .multipass_qpt import pauli_matrices


@dataclass(frozen=True)
class ChoiPhysicality:
    min_eigenvalue: float
    negative_eigenvalue_sum: float
    trace_preserving_residual: float
    trace_value: float


@dataclass(frozen=True)
class ProjectedQPTResult:
    raw_choi: np.ndarray
    psd_choi: np.ndarray
    cptp_choi: np.ndarray
    raw_ptm: np.ndarray
    psd_ptm: np.ndarray
    cptp_ptm: np.ndarray
    raw_physicality: ChoiPhysicality
    psd_physicality: ChoiPhysicality
    cptp_physicality: ChoiPhysicality


def matrix_unit(row: int, col: int, dim: int = 2) -> np.ndarray:
    matrix = np.zeros((dim, dim), dtype=complex)
    matrix[int(row), int(col)] = 1.0
    return matrix


def stokes_to_density(stokes: np.ndarray) -> np.ndarray:
    basis = pauli_matrices()
    values = np.asarray(stokes, dtype=complex)
    if values.shape != (4,):
        raise ValueError("single-qubit Stokes vector must have shape (4,)")
    rho = sum(values[idx] * basis[idx] for idx in range(4)) / 2.0
    return np.asarray(rho, dtype=complex)


def density_to_stokes(rho: np.ndarray) -> np.ndarray:
    matrix = np.asarray(rho, dtype=complex)
    return np.array([np.trace(pauli @ matrix) for pauli in pauli_matrices()], dtype=complex)


def apply_ptm_to_density(ptm: np.ndarray, rho: np.ndarray) -> np.ndarray:
    stokes_in = density_to_stokes(rho)
    stokes_out = np.asarray(ptm, dtype=complex) @ stokes_in
    return stokes_to_density(stokes_out)


def ptm_to_choi(ptm: np.ndarray) -> np.ndarray:
    dim = 2
    choi = np.zeros((dim * dim, dim * dim), dtype=complex)
    for row in range(dim):
        for col in range(dim):
            input_unit = matrix_unit(row, col, dim=dim)
            output = apply_ptm_to_density(ptm, input_unit)
            choi += np.kron(input_unit, output)
    return 0.5 * (choi + choi.conj().T)


def choi_to_ptm(choi: np.ndarray) -> np.ndarray:
    dim = 2
    matrix = np.asarray(choi, dtype=complex)
    basis = pauli_matrices()
    ptm = np.zeros((4, 4), dtype=float)
    for col, pauli_in in enumerate(basis):
        output = np.zeros((dim, dim), dtype=complex)
        for row_idx in range(dim):
            for col_idx in range(dim):
                block = matrix[
                    row_idx * dim : (row_idx + 1) * dim,
                    col_idx * dim : (col_idx + 1) * dim,
                ]
                output += pauli_in[row_idx, col_idx] * block
        for row, pauli_out in enumerate(basis):
            ptm[row, col] = float(np.real_if_close(np.trace(pauli_out @ output) / 2.0).real)
    ptm[0, :] = np.real_if_close(ptm[0, :]).real
    return ptm


def partial_trace_output(choi: np.ndarray, dim: int = 2) -> np.ndarray:
    matrix = np.asarray(choi, dtype=complex).reshape(dim, dim, dim, dim)
    return np.einsum("abcb->ac", matrix)


def project_trace_preserving(choi: np.ndarray, dim: int = 2) -> np.ndarray:
    matrix = np.asarray(choi, dtype=complex)
    correction_in = (np.eye(dim, dtype=complex) - partial_trace_output(matrix, dim=dim)) / dim
    projected = matrix + np.kron(correction_in, np.eye(dim, dtype=complex))
    return 0.5 * (projected + projected.conj().T)


def project_positive_semidefinite(choi: np.ndarray) -> np.ndarray:
    matrix = 0.5 * (np.asarray(choi, dtype=complex) + np.asarray(choi, dtype=complex).conj().T)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    clipped = np.clip(eigenvalues.real, 0.0, None)
    projected = eigenvectors @ np.diag(clipped) @ eigenvectors.conj().T
    return 0.5 * (projected + projected.conj().T)


def project_cptp_dykstra(
    choi: np.ndarray,
    iterations: int = 120,
    dim: int = 2,
) -> np.ndarray:
    """Project a Choi matrix onto the CPTP intersection using Dykstra steps."""

    x_mat = 0.5 * (np.asarray(choi, dtype=complex) + np.asarray(choi, dtype=complex).conj().T)
    p_psd = np.zeros_like(x_mat)
    p_tp = np.zeros_like(x_mat)
    for _ in range(int(iterations)):
        y_mat = project_positive_semidefinite(x_mat + p_psd)
        p_psd = x_mat + p_psd - y_mat
        x_next = project_trace_preserving(y_mat + p_tp, dim=dim)
        p_tp = y_mat + p_tp - x_next
        x_mat = x_next
    return 0.5 * (x_mat + x_mat.conj().T)


def choi_physicality(choi: np.ndarray, dim: int = 2) -> ChoiPhysicality:
    matrix = 0.5 * (np.asarray(choi, dtype=complex) + np.asarray(choi, dtype=complex).conj().T)
    eigenvalues = np.linalg.eigvalsh(matrix).real
    negative = eigenvalues[eigenvalues < 0.0]
    tp_residual = np.linalg.norm(partial_trace_output(matrix, dim=dim) - np.eye(dim))
    return ChoiPhysicality(
        min_eigenvalue=float(np.min(eigenvalues)),
        negative_eigenvalue_sum=float(np.sum(np.abs(negative))),
        trace_preserving_residual=float(tp_residual),
        trace_value=float(np.real(np.trace(matrix))),
    )


def projected_least_squares_qpt(raw_ptm: np.ndarray, iterations: int = 120) -> ProjectedQPTResult:
    raw_choi = ptm_to_choi(raw_ptm)
    psd_choi = project_positive_semidefinite(raw_choi)
    cptp_choi = project_cptp_dykstra(raw_choi, iterations=iterations)
    return ProjectedQPTResult(
        raw_choi=raw_choi,
        psd_choi=psd_choi,
        cptp_choi=cptp_choi,
        raw_ptm=np.asarray(raw_ptm, dtype=float),
        psd_ptm=choi_to_ptm(psd_choi),
        cptp_ptm=choi_to_ptm(cptp_choi),
        raw_physicality=choi_physicality(raw_choi),
        psd_physicality=choi_physicality(psd_choi),
        cptp_physicality=choi_physicality(cptp_choi),
    )


def choi_frobenius_error(estimated: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(estimated, dtype=complex) - np.asarray(reference, dtype=complex)))
