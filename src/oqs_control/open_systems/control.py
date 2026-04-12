from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm


@dataclass(frozen=True)
class ControlSegment:
    duration: float
    hamiltonian: np.ndarray


def piecewise_constant_propagator(
    segments: list[ControlSegment] | tuple[ControlSegment, ...]
) -> np.ndarray:
    if not segments:
        raise ValueError("segments must not be empty")
    dim = np.asarray(segments[0].hamiltonian).shape[0]
    total = np.eye(dim, dtype=complex)
    for segment in segments:
        if segment.duration < 0:
            raise ValueError("segment duration must be non-negative")
        total = expm(-1j * np.asarray(segment.hamiltonian, dtype=complex) * segment.duration) @ total
    return total


def gate_fidelity(u_target: np.ndarray, u_realized: np.ndarray) -> float:
    target = np.asarray(u_target, dtype=complex)
    realized = np.asarray(u_realized, dtype=complex)
    dim = target.shape[0]
    overlap = np.trace(target.conj().T @ realized)
    return float((np.abs(overlap) ** 2) / (dim**2))
