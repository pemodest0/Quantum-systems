from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from ...open_systems.lindblad import (
    density_matrix_to_vector,
    liouvillian,
    vector_to_density_matrix,
)
from .config import NMRConfig
from .hamiltonians import build_hoffset, build_hrf


@dataclass(frozen=True)
class AlgebraicFIDResult:
    """One-pulse spin-3/2 result propagated in Liouville space."""

    time_s: np.ndarray
    fid: np.ndarray
    states: np.ndarray


def unitary_superoperator(unitary: np.ndarray) -> np.ndarray:
    """Return the Liouville-space superoperator for rho -> U rho U dagger."""

    u = np.asarray(unitary, dtype=complex)
    return np.kron(u.conj(), u)


def detector_row(detector: np.ndarray) -> np.ndarray:
    """Return row d such that d @ vec(rho) = Tr(rho detector)."""

    return np.asarray(detector, dtype=complex).T.reshape(-1, order="F")


def trace_row(dim: int) -> np.ndarray:
    """Return row t such that t @ vec(rho) = Tr(rho)."""

    return np.eye(dim, dtype=complex).reshape(-1, order="F")


def rf_pulse_unitary(
    config: NMRConfig,
    b1_scale: float = 1.0,
    phase_rad: float | None = None,
    duration_s: float | None = None,
    b0_offset_hz: float = 0.0,
    include_quadrupolar_during_pulse: bool = True,
    include_bloch_siegert: bool = True,
) -> np.ndarray:
    """Build a spin-3/2 RF pulse unitary with optional internal evolution."""

    if b1_scale < 0.0:
        raise ValueError("b1_scale must be non-negative")
    duration = config.t_pi2 if duration_s is None else float(duration_s)
    if duration < 0.0:
        raise ValueError("duration_s must be non-negative")

    phase = config.fi_pulse if phase_rad is None else float(phase_rad)
    h_rf = build_hrf(config.wp * b1_scale, config.i_x, config.i_y, phase)
    h = h_rf
    if include_quadrupolar_during_pulse:
        h = h + config.h_free + build_hoffset(b0_offset_hz, config.i_z)
    if include_bloch_siegert:
        h = h + config.h_bs
    return expm(-1j * h * duration)


def free_liouvillian(
    config: NMRConfig,
    b0_offset_hz: float = 0.0,
    jump_operators: tuple[np.ndarray, ...] | list[np.ndarray] | None = None,
) -> np.ndarray:
    h_free = config.h_free + build_hoffset(b0_offset_hz, config.i_z)
    return liouvillian(h_free, jump_operators)


def simulate_algebraic_one_pulse_fid(
    config: NMRConfig,
    n_points: int | None = None,
    rho0: np.ndarray | None = None,
    b0_offset_hz: float = 0.0,
    b1_scale: float = 1.0,
    include_dead_time: bool = True,
    include_quadrupolar_during_pulse: bool = True,
    conjugate_output: bool = True,
) -> AlgebraicFIDResult:
    """Simulate the reference one-pulse experiment by explicit superoperators."""

    total_points = n_points or config.n_acq
    if total_points <= 0:
        raise ValueError("n_points must be positive")

    pulse_u = rf_pulse_unitary(
        config,
        b1_scale=b1_scale,
        b0_offset_hz=b0_offset_hz,
        include_quadrupolar_during_pulse=include_quadrupolar_during_pulse,
    )
    pulse_s = unitary_superoperator(pulse_u)
    l_free = free_liouvillian(config, b0_offset_hz=b0_offset_hz)
    dwell_s = expm(l_free * config.dwell_time)
    dead_s = expm(l_free * config.t_evol_total)

    rho_init = config.rho_eq if rho0 is None else np.asarray(rho0, dtype=complex)
    rho_vec = pulse_s @ density_matrix_to_vector(rho_init)
    if include_dead_time and config.t_evol_total > 0.0:
        rho_vec = dead_s @ rho_vec

    fid = np.zeros(total_points, dtype=complex)
    states = np.zeros((total_points, config.dim, config.dim), dtype=complex)
    detect = detector_row(config.detector)
    for idx in range(total_points):
        states[idx] = vector_to_density_matrix(rho_vec, config.dim)
        fid[idx] = detect @ rho_vec
        rho_vec = dwell_s @ rho_vec

    time_s = np.arange(total_points, dtype=float) * config.dwell_time
    if conjugate_output:
        fid = np.conj(fid)
    return AlgebraicFIDResult(time_s=time_s, fid=fid, states=states)


def coherence_order_weights(
    rho: np.ndarray,
    m_values: np.ndarray,
    normalize: bool = True,
) -> dict[int, float]:
    """Return Frobenius weight per coherence order q = m_bra - m_ket."""

    state = np.asarray(rho, dtype=complex)
    m = np.asarray(m_values, dtype=float)
    orders = np.rint(m[:, None] - m[None, :]).astype(int)
    weights: dict[int, float] = {}
    for order in range(int(np.min(orders)), int(np.max(orders)) + 1):
        mask = orders == order
        weights[order] = float(np.sum(np.abs(state[mask]) ** 2))

    if normalize:
        total = sum(weights.values())
        if total > 0.0:
            weights = {order: value / total for order, value in weights.items()}
    return weights


def deviation_density(config: NMRConfig) -> np.ndarray:
    """Return the traceless high-temperature deviation density matrix."""

    return config.rho_eq - np.eye(config.dim, dtype=complex) / config.dim


def signal_energy(fid: np.ndarray) -> float:
    """Return a scale-invariant FID energy proxy for B0/B1 maps."""

    values = np.asarray(fid, dtype=complex)
    return float(np.sqrt(np.mean(np.abs(values) ** 2)))
