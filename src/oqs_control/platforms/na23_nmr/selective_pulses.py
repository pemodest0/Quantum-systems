from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from .config import NMRConfig
from .tomography import reconstruct_density_matrix, simulate_tomography_signals, state_fidelity


@dataclass(frozen=True)
class SelectivePulseResult:
    transition_label: str
    transition_pair: tuple[int, int]
    pulse_duration_s: float
    target_unitary: np.ndarray
    actual_unitary: np.ndarray
    operator_fidelity: float
    mean_state_fidelity: float
    min_state_fidelity: float


def transition_axis(dim: int, pair: tuple[int, int], phase_rad: float = 0.0) -> np.ndarray:
    """Return a two-level RF axis embedded in the spin-3/2 Hilbert space."""

    row, col = pair
    if row == col or not (0 <= row < dim) or not (0 <= col < dim):
        raise ValueError("pair must contain two distinct valid basis indices")
    x_axis = np.zeros((dim, dim), dtype=complex)
    y_axis = np.zeros((dim, dim), dtype=complex)
    x_axis[row, col] = 1.0
    x_axis[col, row] = 1.0
    y_axis[row, col] = -1j
    y_axis[col, row] = 1j
    return np.cos(phase_rad) * x_axis + np.sin(phase_rad) * y_axis


def ideal_selective_rotation(
    dim: int,
    pair: tuple[int, int],
    angle_rad: float,
    phase_rad: float = 0.0,
) -> np.ndarray:
    """Return the ideal selective rotation acting only on one transition."""

    h_axis = 0.5 * float(angle_rad) * transition_axis(dim, pair, phase_rad)
    return expm(-1j * h_axis)


def transition_frequency_rad_s(config: NMRConfig, pair: tuple[int, int]) -> float:
    """Return the angular frequency splitting for one adjacent transition."""

    row, col = pair
    energies = np.diag(config.h_free).real
    return float(energies[row] - energies[col])


def selected_transition_frame_hamiltonian(
    config: NMRConfig,
    pair: tuple[int, int],
    carrier_detuning_hz: float = 0.0,
) -> np.ndarray:
    """Return H_free in the frame resonant with a selected transition."""

    row, col = pair
    delta_m = float(config.m_vals[row] - config.m_vals[col])
    if abs(delta_m) < 1e-15:
        raise ValueError("selected transition must have non-zero delta m")
    carrier_rad_s = transition_frequency_rad_s(config, pair) / delta_m
    carrier_rad_s += 2.0 * np.pi * float(carrier_detuning_hz)
    h_rot = config.h_free - carrier_rad_s * config.i_z
    return h_rot - np.trace(h_rot) * np.eye(config.dim, dtype=complex) / config.dim


def finite_selective_pulse_unitary(
    config: NMRConfig,
    pair: tuple[int, int],
    angle_rad: float,
    duration_s: float,
    phase_rad: float = 0.0,
    carrier_detuning_hz: float = 0.0,
    include_quadrupolar_evolution: bool = True,
) -> np.ndarray:
    """Return a finite selective-pulse propagator for one spin-3/2 transition."""

    if duration_s <= 0.0:
        raise ValueError("duration_s must be positive")
    omega1_rad_s = float(angle_rad) / float(duration_s)
    h_control = 0.5 * omega1_rad_s * transition_axis(config.dim, pair, phase_rad)
    h_total = h_control
    if include_quadrupolar_evolution:
        h_total = h_total + selected_transition_frame_hamiltonian(
            config,
            pair,
            carrier_detuning_hz=carrier_detuning_hz,
        )
    return expm(-1j * h_total * float(duration_s))


def unitary_operator_fidelity(target: np.ndarray, actual: np.ndarray) -> float:
    """Return global-phase-insensitive unitary process overlap."""

    u_target = np.asarray(target, dtype=complex)
    u_actual = np.asarray(actual, dtype=complex)
    dim = u_target.shape[0]
    return float(np.clip(abs(np.trace(u_target.conj().T @ u_actual)) ** 2 / dim**2, 0.0, 1.0))


def probe_states(dim: int) -> tuple[np.ndarray, ...]:
    """Return basis and superposition states for selective-pulse benchmarks."""

    states: list[np.ndarray] = []
    for idx in range(dim):
        vector = np.zeros(dim, dtype=complex)
        vector[idx] = 1.0
        states.append(np.outer(vector, vector.conj()))

    phases = np.array([0.0, 0.19 * np.pi, 0.53 * np.pi, 1.11 * np.pi], dtype=float)
    coherent = np.exp(1j * phases[:dim])
    coherent = coherent / np.linalg.norm(coherent)
    states.append(np.outer(coherent, coherent.conj()))

    balanced = np.zeros(dim, dtype=complex)
    balanced[1] = 1.0
    balanced[2] = 1.0j
    balanced = balanced / np.linalg.norm(balanced)
    states.append(np.outer(balanced, balanced.conj()))

    return tuple(states)


def mean_state_fidelity_for_unitaries(
    target: np.ndarray,
    actual: np.ndarray,
    states: tuple[np.ndarray, ...],
) -> tuple[float, float]:
    fidelities: list[float] = []
    for rho in states:
        target_state = target @ rho @ target.conj().T
        actual_state = actual @ rho @ actual.conj().T
        fidelities.append(
            float(np.clip(np.real(np.trace(target_state @ actual_state)), 0.0, 1.0))
        )
    return float(np.mean(fidelities)), float(np.min(fidelities))


def evaluate_selective_pulse(
    config: NMRConfig,
    transition_index: int,
    angle_rad: float,
    duration_s: float,
    phase_rad: float = 0.0,
    include_quadrupolar_evolution: bool = True,
    carrier_detuning_hz: float = 0.0,
) -> SelectivePulseResult:
    pair = config.transition_pairs[transition_index]
    target = ideal_selective_rotation(config.dim, pair, angle_rad, phase_rad)
    actual = finite_selective_pulse_unitary(
        config,
        pair,
        angle_rad,
        duration_s,
        phase_rad=phase_rad,
        carrier_detuning_hz=carrier_detuning_hz,
        include_quadrupolar_evolution=include_quadrupolar_evolution,
    )
    mean_fid, min_fid = mean_state_fidelity_for_unitaries(target, actual, probe_states(config.dim))
    return SelectivePulseResult(
        transition_label=config.transition_labels[transition_index],
        transition_pair=pair,
        pulse_duration_s=float(duration_s),
        target_unitary=target,
        actual_unitary=actual,
        operator_fidelity=unitary_operator_fidelity(target, actual),
        mean_state_fidelity=mean_fid,
        min_state_fidelity=min_fid,
    )


def population_transfer_probability(
    unitary: np.ndarray,
    initial_index: int,
    final_index: int,
) -> float:
    return float(abs(unitary[int(final_index), int(initial_index)]) ** 2)


def qst_monitor_selective_pulse(
    config: NMRConfig,
    unitary: np.ndarray,
    initial_state: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return true output, QST reconstruction, and reconstruction fidelity."""

    true_output = unitary @ initial_state @ unitary.conj().T
    signals = simulate_tomography_signals(true_output, config)
    qst = reconstruct_density_matrix(signals, config, rho_true=true_output)
    return true_output, qst.reconstructed_rho, float(qst.fidelity or 0.0)
