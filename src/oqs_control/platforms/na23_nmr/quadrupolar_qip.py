from __future__ import annotations

from dataclasses import dataclass

import numpy as np


COMPUTATIONAL_BASIS = ("00", "01", "10", "11")


@dataclass(frozen=True)
class GroverResult:
    marked_index: int
    epsilon: float
    initial_state: np.ndarray
    uniform_state: np.ndarray
    final_state: np.ndarray
    final_populations: np.ndarray
    marked_population: float
    deviation_fidelity: float


def pauli_matrices() -> dict[str, np.ndarray]:
    return {
        "I": np.eye(2, dtype=complex),
        "X": np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex),
        "Y": np.array([[0.0, -1j], [1j, 0.0]], dtype=complex),
        "Z": np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex),
    }


def hadamard() -> np.ndarray:
    return np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / np.sqrt(2.0)


def two_qubit_product(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.kron(np.asarray(left, dtype=complex), np.asarray(right, dtype=complex))


def two_qubit_hadamard() -> np.ndarray:
    return two_qubit_product(hadamard(), hadamard())


def logical_product_operator_basis() -> dict[str, np.ndarray]:
    paulis = pauli_matrices()
    return {
        left + right: two_qubit_product(paulis[left], paulis[right])
        for left in ("I", "X", "Y", "Z")
        for right in ("I", "X", "Y", "Z")
    }


def basis_state(index: int, dim: int = 4) -> np.ndarray:
    if not 0 <= int(index) < dim:
        raise ValueError("basis-state index out of range")
    vector = np.zeros(dim, dtype=complex)
    vector[int(index)] = 1.0
    return vector


def projector(index: int, dim: int = 4) -> np.ndarray:
    vector = basis_state(index, dim=dim)
    return np.outer(vector, vector.conj())


def pseudo_pure_state(index: int, epsilon: float, dim: int = 4) -> np.ndarray:
    """Return (1-epsilon) I/d + epsilon |index><index|.

    In liquid-state NMR, the identity part is not directly observed. The
    epsilon-scaled deviation density carries the computational signal.
    """

    if not 0.0 <= float(epsilon) <= 1.0:
        raise ValueError("epsilon must satisfy 0 <= epsilon <= 1")
    mixed = np.eye(dim, dtype=complex) / dim
    state = (1.0 - float(epsilon)) * mixed + float(epsilon) * projector(index, dim=dim)
    return state / np.trace(state)


def deviation_density(rho: np.ndarray) -> np.ndarray:
    matrix = np.asarray(rho, dtype=complex)
    dim = matrix.shape[0]
    return matrix - np.trace(matrix) * np.eye(dim, dtype=complex) / dim


def deviation_fidelity(rho: np.ndarray, target: np.ndarray) -> float:
    """Hilbert-Schmidt cosine between two traceless NMR deviation densities."""

    dev_a = deviation_density(rho)
    dev_b = deviation_density(target)
    norm_a = float(np.linalg.norm(dev_a))
    norm_b = float(np.linalg.norm(dev_b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    overlap = float(np.real(np.trace(dev_a.conj().T @ dev_b)))
    return float(np.clip(overlap / (norm_a * norm_b), -1.0, 1.0))


def oracle(marked_index: int, dim: int = 4) -> np.ndarray:
    return np.eye(dim, dtype=complex) - 2.0 * projector(marked_index, dim=dim)


def diffusion_operator(dim: int = 4) -> np.ndarray:
    uniform = np.ones(dim, dtype=complex) / np.sqrt(float(dim))
    return 2.0 * np.outer(uniform, uniform.conj()) - np.eye(dim, dtype=complex)


def grover_iteration(marked_index: int, dim: int = 4) -> np.ndarray:
    return diffusion_operator(dim=dim) @ oracle(marked_index, dim=dim)


def grover_search_unitary(marked_index: int, dim: int = 4) -> np.ndarray:
    if dim != 4:
        raise ValueError("this project benchmark implements the two-qubit dim=4 Grover case")
    return grover_iteration(marked_index, dim=dim) @ two_qubit_hadamard()


def run_grover_search(marked_index: int, epsilon: float = 1.0) -> GroverResult:
    rho0 = pseudo_pure_state(0, epsilon=epsilon, dim=4)
    h2 = two_qubit_hadamard()
    uniform = h2 @ rho0 @ h2.conj().T
    unitary = grover_search_unitary(marked_index, dim=4)
    final = unitary @ rho0 @ unitary.conj().T
    final = 0.5 * (final + final.conj().T)
    final = final / np.trace(final)
    populations = np.real(np.diag(final))
    target = pseudo_pure_state(marked_index, epsilon=epsilon, dim=4)
    return GroverResult(
        marked_index=int(marked_index),
        epsilon=float(epsilon),
        initial_state=rho0,
        uniform_state=uniform,
        final_state=final,
        final_populations=populations,
        marked_population=float(populations[int(marked_index)]),
        deviation_fidelity=deviation_fidelity(final, target),
    )


def decompose_in_product_operator_basis(matrix: np.ndarray) -> dict[str, float]:
    """Return real coefficients in the two-qubit Pauli product basis.

    The basis matrices satisfy Tr(P_a P_b) = 4 delta_ab for the dim=4 logical
    encoding used by spin-3/2 quadrupolar NMR.
    """

    op = np.asarray(matrix, dtype=complex)
    coeffs: dict[str, float] = {}
    for label, basis in logical_product_operator_basis().items():
        coeffs[label] = float(np.real_if_close(np.trace(basis.conj().T @ op) / 4.0).real)
    return coeffs


def reconstruct_from_product_coefficients(coefficients: dict[str, float]) -> np.ndarray:
    basis = logical_product_operator_basis()
    matrix = np.zeros((4, 4), dtype=complex)
    for label, value in coefficients.items():
        matrix = matrix + float(value) * basis[label]
    return matrix


def quadrupolar_traceless_operator(i_spin: float, i_z2: np.ndarray) -> np.ndarray:
    dim = i_z2.shape[0]
    return 3.0 * np.asarray(i_z2, dtype=complex) - i_spin * (i_spin + 1.0) * np.eye(
        dim,
        dtype=complex,
    )


def logical_correlation_vector(rho: np.ndarray) -> dict[str, float]:
    matrix = np.asarray(rho, dtype=complex)
    return {
        label: float(np.real_if_close(np.trace(matrix @ basis)).real)
        for label, basis in logical_product_operator_basis().items()
    }
