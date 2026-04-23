from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm


@dataclass(frozen=True)
class MasterEquationResult:
    times: np.ndarray
    states: np.ndarray


def density_matrix_to_vector(rho: np.ndarray) -> np.ndarray:
    return np.asarray(rho, dtype=complex).reshape(-1, order="F")


def vector_to_density_matrix(vec: np.ndarray, dim: int) -> np.ndarray:
    return np.asarray(vec, dtype=complex).reshape((dim, dim), order="F")


def liouvillian(
    hamiltonian: np.ndarray,
    jump_operators: list[np.ndarray] | tuple[np.ndarray, ...] | None = None,
) -> np.ndarray:
    h = np.asarray(hamiltonian, dtype=complex)
    dim = h.shape[0]
    identity = np.eye(dim, dtype=complex)
    jumps = list(jump_operators or [])

    commutator = -1j * (np.kron(identity, h) - np.kron(h.T, identity))
    dissipator = np.zeros_like(commutator)
    for jump in jumps:
        c_op = np.asarray(jump, dtype=complex)
        c_dag_c = c_op.conj().T @ c_op
        dissipator = dissipator + np.kron(c_op.conj(), c_op)
        dissipator = dissipator - 0.5 * np.kron(identity, c_dag_c)
        dissipator = dissipator - 0.5 * np.kron(c_dag_c.T, identity)

    return commutator + dissipator


def mesolve(
    hamiltonian: np.ndarray,
    rho0: np.ndarray,
    times: np.ndarray,
    jump_operators: list[np.ndarray] | tuple[np.ndarray, ...] | None = None,
) -> MasterEquationResult:
    t = np.asarray(times, dtype=float)
    if t.ndim != 1 or t.size < 2:
        raise ValueError("times must be a one-dimensional array with at least two entries")

    rho_init = np.asarray(rho0, dtype=complex)
    dim = rho_init.shape[0]
    l_op = liouvillian(hamiltonian, jump_operators)
    rho_vec = density_matrix_to_vector(rho_init)
    states = np.zeros((t.size, dim, dim), dtype=complex)
    states[0] = rho_init

    previous_dt: float | None = None
    propagator: np.ndarray | None = None
    for idx in range(1, t.size):
        dt = float(t[idx] - t[idx - 1])
        if dt <= 0:
            raise ValueError("times must be strictly increasing")
        if previous_dt is None or propagator is None or not np.isclose(dt, previous_dt):
            propagator = expm(l_op * dt)
            previous_dt = dt
        rho_vec = propagator @ rho_vec
        states[idx] = vector_to_density_matrix(rho_vec, dim)

    return MasterEquationResult(times=t, states=states)


def expectation_values(states: np.ndarray, observable: np.ndarray) -> np.ndarray:
    obs = np.asarray(observable, dtype=complex)
    return np.array([np.trace(rho @ obs) for rho in states], dtype=complex)
