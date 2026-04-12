from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from ...open_systems.lindblad import (
    density_matrix_to_vector,
    liouvillian,
    vector_to_density_matrix,
)
from ...open_systems.statistical_mechanics import (
    entropy_production_proxy,
    free_energy_like,
    purity,
    relative_entropy,
    von_neumann_entropy,
)
from .analysis import fft_spectrum
from .config import NMRConfig


@dataclass(frozen=True)
class NMRDissipationRates:
    """Effective rates in s^-1 for the first Na-23 open-system model."""

    gamma_phi: float = 160.0
    gamma_relax: float = 35.0


@dataclass(frozen=True)
class PhysicalChecks:
    max_trace_error: float
    max_hermiticity_error: float
    min_eigenvalue: float


@dataclass(frozen=True)
class OpenNMRSimulationResult:
    time_s: np.ndarray
    fid: np.ndarray
    spectrum: np.ndarray
    freq_hz: np.ndarray
    states: np.ndarray
    checks: PhysicalChecks
    purity: np.ndarray
    entropy: np.ndarray
    relative_entropy_to_mixed: np.ndarray
    entropy_production_proxy: np.ndarray
    free_energy_like: np.ndarray
    rates: NMRDissipationRates


def _transition_operator(dim: int, row: int, col: int) -> np.ndarray:
    op = np.zeros((dim, dim), dtype=complex)
    op[row, col] = 1.0
    return op


def effective_jump_operators(
    config: NMRConfig,
    rates: NMRDissipationRates,
) -> tuple[np.ndarray, ...]:
    """Build a minimal effective dissipator for the spin-3/2 manifold.

    The model is intentionally effective: `I_z` dephasing captures loss of
    phase coherence, while symmetric nearest-neighbor jumps capture population
    relaxation without imposing a microscopic bath model.
    """

    if rates.gamma_phi < 0 or rates.gamma_relax < 0:
        raise ValueError("Dissipation rates must be non-negative")

    jumps: list[np.ndarray] = []
    if rates.gamma_phi > 0:
        jumps.append(np.sqrt(rates.gamma_phi) * config.i_z)

    if rates.gamma_relax > 0:
        per_transition = rates.gamma_relax / max(len(config.transition_pairs), 1)
        for row, col in config.transition_pairs:
            jumps.append(np.sqrt(per_transition) * _transition_operator(config.dim, row, col))
            jumps.append(np.sqrt(per_transition) * _transition_operator(config.dim, col, row))

    return tuple(jumps)


def nmr_liouvillian(
    config: NMRConfig,
    rates: NMRDissipationRates | None = None,
    hamiltonian: np.ndarray | None = None,
) -> np.ndarray:
    active_rates = rates or NMRDissipationRates()
    h = np.asarray(hamiltonian if hamiltonian is not None else config.h_free, dtype=complex)
    return liouvillian(h, effective_jump_operators(config, active_rates))


def physical_checks(states: np.ndarray) -> PhysicalChecks:
    traces = np.trace(states, axis1=1, axis2=2)
    trace_error = np.max(np.abs(traces - 1.0))
    hermiticity_error = np.max(np.abs(states - np.conjugate(np.swapaxes(states, 1, 2))))
    min_eval = min(
        float(np.min(np.linalg.eigvalsh(0.5 * (rho + rho.conj().T)).real))
        for rho in states
    )
    return PhysicalChecks(
        max_trace_error=float(trace_error),
        max_hermiticity_error=float(hermiticity_error),
        min_eigenvalue=min_eval,
    )


def _initial_detected_state(config: NMRConfig, rho0: np.ndarray | None = None) -> np.ndarray:
    if rho0 is not None:
        return np.array(rho0, dtype=complex, copy=True)
    return config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T


def simulate_open_fid(
    config: NMRConfig,
    rates: NMRDissipationRates | None = None,
    rho0: np.ndarray | None = None,
    n_points: int | None = None,
    include_dead_time: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate a Na-23 FID by propagating an explicit Liouvillian."""

    active_rates = rates or NMRDissipationRates()
    total_points = n_points or config.n_acq
    l_op = nmr_liouvillian(config, active_rates)
    u_dwell = expm(l_op * config.dwell_time)

    rho = _initial_detected_state(config, rho0=rho0)
    rho_vec = density_matrix_to_vector(rho)
    if include_dead_time and config.t_evol_total > 0:
        rho_vec = expm(l_op * config.t_evol_total) @ rho_vec

    fid = np.zeros(total_points, dtype=complex)
    states = np.zeros((total_points, config.dim, config.dim), dtype=complex)
    for idx in range(total_points):
        rho = vector_to_density_matrix(rho_vec, config.dim)
        states[idx] = rho
        fid[idx] = np.trace(rho @ config.detector)
        rho_vec = u_dwell @ rho_vec

    time_s = np.arange(total_points, dtype=float) * config.dwell_time
    return time_s, np.conj(fid), states


def simulate_open_reference_experiment(
    config: NMRConfig | None = None,
    rates: NMRDissipationRates | None = None,
    n_points: int | None = None,
) -> OpenNMRSimulationResult:
    active_config = config or NMRConfig()
    active_rates = rates or NMRDissipationRates()
    time_s, fid, states = simulate_open_fid(
        active_config,
        rates=active_rates,
        n_points=n_points,
    )
    freq_hz, spectrum = fft_spectrum(fid, active_config.dwell_time)
    mixed = np.eye(active_config.dim, dtype=complex) / active_config.dim
    pur = np.array([purity(rho) for rho in states], dtype=float)
    ent = np.array([von_neumann_entropy(rho) for rho in states], dtype=float)
    rel = np.array([relative_entropy(rho, mixed) for rho in states], dtype=float)
    ent_prod = entropy_production_proxy(states, mixed, time_s)
    free = np.array(
        [
            free_energy_like(
                rho,
                active_config.h_free,
                temperature=max(active_config.temperature_k, 1e-12),
            )
            for rho in states
        ],
        dtype=float,
    )
    return OpenNMRSimulationResult(
        time_s=time_s,
        fid=fid,
        spectrum=spectrum,
        freq_hz=freq_hz,
        states=states,
        checks=physical_checks(states),
        purity=pur,
        entropy=ent,
        relative_entropy_to_mixed=rel,
        entropy_production_proxy=ent_prod,
        free_energy_like=free,
        rates=active_rates,
    )
