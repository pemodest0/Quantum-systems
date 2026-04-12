from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import NMRConfig
from .tomography import TomographyResult, reconstruct_density_matrix, simulate_tomography_signals


@dataclass(frozen=True)
class QSTRelaxationRates:
    """Synthetic rates used in the Paper C tomography-relaxation benchmark."""

    gamma_population: float = 55.0
    gamma_dephasing: float = 45.0


@dataclass(frozen=True)
class QSTTrajectory:
    label: str
    times_s: np.ndarray
    true_states: np.ndarray
    reconstructed_states: np.ndarray
    fidelities: np.ndarray
    frobenius_errors: np.ndarray
    residual_norms: np.ndarray


@dataclass(frozen=True)
class QSTRateEstimate:
    gamma_population: float
    gamma_dephasing: float
    coherence_order_rates: dict[int, float]
    population_fit_rmse: float
    coherence_fit_rmse: float


def pure_state_density(vector: np.ndarray) -> np.ndarray:
    state = np.asarray(vector, dtype=complex)
    norm = np.linalg.norm(state)
    if norm <= 0.0:
        raise ValueError("state vector norm must be positive")
    state = state / norm
    return np.outer(state, state.conj())


def coherent_superposition_state(dim: int = 4) -> np.ndarray:
    phases = np.array([0.0, 0.31 * np.pi, 0.83 * np.pi, 1.27 * np.pi], dtype=float)
    return pure_state_density(np.exp(1j * phases[:dim]))


def population_biased_state(dim: int = 4, occupied_index: int = 0) -> np.ndarray:
    vector = np.zeros(dim, dtype=complex)
    vector[int(occupied_index)] = 1.0
    return pure_state_density(vector)


def mix_with_identity(rho: np.ndarray, mixing: float = 0.02) -> np.ndarray:
    """Return (1 - mixing) rho + mixing I/d with trace normalization."""

    if not 0.0 <= mixing < 1.0:
        raise ValueError("mixing must satisfy 0 <= mixing < 1")
    state = np.asarray(rho, dtype=complex)
    dim = state.shape[0]
    mixed = (1.0 - mixing) * state + mixing * np.eye(dim, dtype=complex) / dim
    return mixed / np.trace(mixed)


def synthetic_quadrupolar_relaxation_state(
    rho0: np.ndarray,
    time_s: float,
    config: NMRConfig,
    rates: QSTRelaxationRates,
    include_unitary_phase: bool = True,
) -> np.ndarray:
    """Apply a CP-inspired synthetic population/dephasing relaxation channel."""

    if rates.gamma_population < 0.0 or rates.gamma_dephasing < 0.0:
        raise ValueError("relaxation rates must be non-negative")
    if time_s < 0.0:
        raise ValueError("time_s must be non-negative")

    rho = np.asarray(rho0, dtype=complex)
    dim = config.dim
    mixed = np.eye(dim, dtype=complex) / dim
    population_factor = np.exp(-rates.gamma_population * float(time_s))
    relaxed = population_factor * rho + (1.0 - population_factor) * mixed

    m = np.asarray(config.m_vals, dtype=float)
    q_orders = np.rint(m[:, None] - m[None, :]).astype(int)
    dephasing = np.exp(-rates.gamma_dephasing * (q_orders.astype(float) ** 2) * float(time_s))
    relaxed = relaxed * dephasing

    if include_unitary_phase:
        energies = np.diag(config.h_free).real
        phase = np.exp(-1j * (energies[:, None] - energies[None, :]) * float(time_s))
        relaxed = relaxed * phase

    relaxed = 0.5 * (relaxed + relaxed.conj().T)
    trace = np.trace(relaxed)
    if abs(trace) == 0.0:
        raise ValueError("relaxed state has zero trace")
    return relaxed / trace


def synthetic_relaxation_trajectory(
    rho0: np.ndarray,
    times_s: np.ndarray,
    config: NMRConfig,
    rates: QSTRelaxationRates,
    include_unitary_phase: bool = True,
) -> np.ndarray:
    times = np.asarray(times_s, dtype=float)
    if times.ndim != 1:
        raise ValueError("times_s must be one-dimensional")
    return np.array(
        [
            synthetic_quadrupolar_relaxation_state(
                rho0,
                float(time_s),
                config,
                rates,
                include_unitary_phase=include_unitary_phase,
            )
            for time_s in times
        ],
        dtype=complex,
    )


def add_tomography_noise(
    signals: np.ndarray,
    noise_std: float,
    rng: np.random.Generator,
    phase_error_rad: float = 0.0,
) -> np.ndarray:
    noisy = np.array(signals, dtype=complex, copy=True)
    if phase_error_rad != 0.0:
        phase_indices = np.arange(noisy.shape[0], dtype=float)
        centered = phase_indices - float(np.mean(phase_indices))
        noisy = noisy * np.exp(1j * phase_error_rad * centered)[:, None]
    if noise_std > 0.0:
        scale = max(float(np.max(np.abs(signals))), 1e-15)
        noise = rng.normal(size=noisy.shape) + 1j * rng.normal(size=noisy.shape)
        noisy = noisy + noise_std * scale * noise / np.sqrt(2.0)
    return noisy


def reconstruct_qst_trajectory(
    label: str,
    true_states: np.ndarray,
    times_s: np.ndarray,
    config: NMRConfig,
    noise_std: float = 0.0,
    phase_error_rad: float = 0.0,
    random_seed: int = 1234,
    enforce_psd: bool = True,
) -> QSTTrajectory:
    rng = np.random.default_rng(random_seed)
    reconstructed: list[np.ndarray] = []
    fidelities: list[float] = []
    frobenius: list[float] = []
    residuals: list[float] = []

    for rho_true in true_states:
        signals = simulate_tomography_signals(rho_true, config)
        measured = add_tomography_noise(signals, noise_std, rng, phase_error_rad=phase_error_rad)
        result: TomographyResult = reconstruct_density_matrix(
            measured,
            config,
            enforce_psd=enforce_psd,
            rho_true=rho_true,
        )
        reconstructed.append(result.reconstructed_rho)
        fidelities.append(float(result.fidelity if result.fidelity is not None else np.nan))
        frobenius.append(float(result.frobenius_error if result.frobenius_error is not None else np.nan))
        residuals.append(float(result.residual_norm))

    return QSTTrajectory(
        label=label,
        times_s=np.asarray(times_s, dtype=float),
        true_states=np.asarray(true_states, dtype=complex),
        reconstructed_states=np.asarray(reconstructed, dtype=complex),
        fidelities=np.asarray(fidelities, dtype=float),
        frobenius_errors=np.asarray(frobenius, dtype=float),
        residual_norms=np.asarray(residuals, dtype=float),
    )


def population_deviation_norms(states: np.ndarray) -> np.ndarray:
    values = np.asarray(states, dtype=complex)
    dim = values.shape[-1]
    mixed_diag = np.ones(dim, dtype=float) / dim
    return np.array(
        [np.linalg.norm(np.real(np.diag(rho)) - mixed_diag) for rho in values],
        dtype=float,
    )


def coherence_order_norms(states: np.ndarray, m_values: np.ndarray) -> dict[int, np.ndarray]:
    values = np.asarray(states, dtype=complex)
    m = np.asarray(m_values, dtype=float)
    q_orders = np.rint(m[:, None] - m[None, :]).astype(int)
    norms: dict[int, np.ndarray] = {}
    for order in range(1, int(np.max(np.abs(q_orders))) + 1):
        mask = np.abs(q_orders) == order
        norms[order] = np.array(
            [np.linalg.norm(rho[mask]) for rho in values],
            dtype=float,
        )
    return norms


def _fit_decay_rate(times_s: np.ndarray, values: np.ndarray) -> tuple[float, float]:
    times = np.asarray(times_s, dtype=float)
    y = np.asarray(values, dtype=float)
    threshold = max(float(np.max(y)) * 1e-6, 1e-12)
    mask = (times > 0.0) & (y > threshold)
    if np.count_nonzero(mask) < 3:
        raise ValueError("not enough non-zero points to fit a decay rate")
    slope, intercept = np.polyfit(times[mask], np.log(y[mask]), 1)
    fitted = slope * times[mask] + intercept
    rmse = float(np.sqrt(np.mean((np.log(y[mask]) - fitted) ** 2)))
    return float(max(0.0, -slope)), rmse


def estimate_rates_from_qst(
    population_trajectory: QSTTrajectory,
    coherence_trajectory: QSTTrajectory,
    m_values: np.ndarray,
) -> QSTRateEstimate:
    gamma_population, pop_rmse = _fit_decay_rate(
        population_trajectory.times_s,
        population_deviation_norms(population_trajectory.reconstructed_states),
    )

    order_norms = coherence_order_norms(coherence_trajectory.reconstructed_states, m_values)
    order_rates: dict[int, float] = {}
    order_rmses: list[float] = []
    dephasing_estimates: list[float] = []
    for order, values in order_norms.items():
        rate, rmse = _fit_decay_rate(coherence_trajectory.times_s, values)
        order_rates[order] = rate
        order_rmses.append(rmse)
        dephasing_estimates.append(max(0.0, (rate - gamma_population) / float(order**2)))

    gamma_dephasing = float(np.median(dephasing_estimates))
    return QSTRateEstimate(
        gamma_population=gamma_population,
        gamma_dephasing=gamma_dephasing,
        coherence_order_rates=order_rates,
        population_fit_rmse=pop_rmse,
        coherence_fit_rmse=float(np.mean(order_rmses)) if order_rmses else np.nan,
    )
