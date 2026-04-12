from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..open_systems.lindblad import expectation_values, mesolve
from ..open_systems.statistical_mechanics import (
    entropy_production_proxy,
    free_energy_like,
    purity,
    von_neumann_entropy,
)


@dataclass(frozen=True)
class OpenQubitDemoResult:
    times: np.ndarray
    states: np.ndarray
    sigma_x_expectation: np.ndarray
    sigma_z_expectation: np.ndarray
    purity: np.ndarray
    entropy: np.ndarray
    entropy_production: np.ndarray
    free_energy_like: np.ndarray


def pauli_x() -> np.ndarray:
    return np.array([[0, 1], [1, 0]], dtype=complex)


def pauli_z() -> np.ndarray:
    return np.array([[1, 0], [0, -1]], dtype=complex)


def sigma_minus() -> np.ndarray:
    return np.array([[0, 0], [1, 0]], dtype=complex)


def projector_ground() -> np.ndarray:
    return np.array([[0, 0], [0, 1]], dtype=complex)


def thermal_like_state(beta: float, omega: float) -> np.ndarray:
    h = 0.5 * omega * pauli_z()
    weights = np.exp(-beta * np.diag(h).real)
    weights = weights / np.sum(weights)
    return np.diag(weights.astype(complex))


def run_open_qubit_demo(
    omega: float = 1.0,
    drive: float = 0.35,
    gamma_relax: float = 0.15,
    gamma_phi: float = 0.08,
    total_time: float = 12.0,
    num_points: int = 400,
    temperature: float = 1.0,
) -> OpenQubitDemoResult:
    sx = pauli_x()
    sz = pauli_z()
    sm = sigma_minus()
    h = 0.5 * omega * sz + drive * sx
    jumps = [np.sqrt(gamma_relax) * sm, np.sqrt(gamma_phi) * sz]

    rho0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    times = np.linspace(0.0, total_time, num_points)
    result = mesolve(h, rho0, times, jump_operators=jumps)

    steady = thermal_like_state(beta=1.0 / max(temperature, 1e-9), omega=omega)
    ex = expectation_values(result.states, sx)
    ez = expectation_values(result.states, sz)
    pur = np.array([purity(rho) for rho in result.states], dtype=float)
    ent = np.array([von_neumann_entropy(rho) for rho in result.states], dtype=float)
    ent_prod = entropy_production_proxy(result.states, steady, result.times)
    free = np.array(
        [free_energy_like(rho, h, temperature=max(temperature, 1e-9)) for rho in result.states],
        dtype=float,
    )

    return OpenQubitDemoResult(
        times=result.times,
        states=result.states,
        sigma_x_expectation=ex,
        sigma_z_expectation=ez,
        purity=pur,
        entropy=ent,
        entropy_production=ent_prod,
        free_energy_like=free,
    )
