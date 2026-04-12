from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MarkovianFit:
    gamma_s: float
    rmse: float
    fitted: np.ndarray


@dataclass(frozen=True)
class MemoryWitness:
    blp_measure: float
    negative_rate_fraction: float
    min_time_local_rate_s: float
    echo_boost_area_s: float
    max_echo_boost: float


def markovian_dephasing_coherence(times_s: np.ndarray, gamma_s: float) -> np.ndarray:
    """Return |coherence| for a semigroup pure-dephasing model."""

    times = np.asarray(times_s, dtype=float)
    if np.any(times < 0.0):
        raise ValueError("times_s must be non-negative")
    if gamma_s < 0.0:
        raise ValueError("gamma_s must be non-negative")
    return np.exp(-float(gamma_s) * times)


def quasi_static_ramsey_coherence(times_s: np.ndarray, sigma_rad_s: float) -> np.ndarray:
    """Return Ramsey coherence for Gaussian quasi-static detuning noise."""

    times = np.asarray(times_s, dtype=float)
    if np.any(times < 0.0):
        raise ValueError("times_s must be non-negative")
    if sigma_rad_s < 0.0:
        raise ValueError("sigma_rad_s must be non-negative")
    return np.exp(-0.5 * (float(sigma_rad_s) * times) ** 2)


def quasi_static_echo_coherence(
    times_s: np.ndarray,
    sigma_rad_s: float,
    refocusing_efficiency: float = 0.95,
) -> np.ndarray:
    """Return Hahn-echo coherence for partially refocused quasi-static noise."""

    if not 0.0 <= refocusing_efficiency <= 1.0:
        raise ValueError("refocusing_efficiency must be between 0 and 1")
    residual_sigma = (1.0 - float(refocusing_efficiency)) * float(sigma_rad_s)
    return quasi_static_ramsey_coherence(times_s, residual_sigma)


def damped_revival_coherence(
    times_s: np.ndarray,
    gamma_s: float,
    omega_rad_s: float,
    phase_rad: float = 0.0,
) -> np.ndarray:
    """Return a bounded damped-oscillatory coherence envelope with revivals."""

    times = np.asarray(times_s, dtype=float)
    if np.any(times < 0.0):
        raise ValueError("times_s must be non-negative")
    if gamma_s < 0.0:
        raise ValueError("gamma_s must be non-negative")
    envelope = np.exp(-float(gamma_s) * times) * np.cos(float(omega_rad_s) * times + phase_rad)
    return np.abs(np.clip(envelope, -1.0, 1.0))


def fit_markovian_dephasing(times_s: np.ndarray, coherence_abs: np.ndarray) -> MarkovianFit:
    """Fit C(t) = exp(-gamma t) to positive coherence magnitudes."""

    times = np.asarray(times_s, dtype=float)
    values = np.asarray(coherence_abs, dtype=float)
    if times.shape != values.shape:
        raise ValueError("times_s and coherence_abs must have the same shape")
    mask = (times > 0.0) & (values > 1e-12)
    if np.count_nonzero(mask) < 3:
        raise ValueError("not enough positive points to fit Markovian dephasing")
    slope, _intercept = np.polyfit(times[mask], np.log(values[mask]), 1)
    gamma = float(max(0.0, -slope))
    fitted = markovian_dephasing_coherence(times, gamma)
    rmse = float(np.sqrt(np.mean((fitted - values) ** 2)))
    return MarkovianFit(gamma_s=gamma, rmse=rmse, fitted=fitted)


def blp_information_backflow(times_s: np.ndarray, trace_distance: np.ndarray) -> float:
    """Discrete Breuer-Laine-Piilo information-backflow proxy."""

    times = np.asarray(times_s, dtype=float)
    distance = np.asarray(trace_distance, dtype=float)
    if times.shape != distance.shape:
        raise ValueError("times_s and trace_distance must have the same shape")
    if times.size < 2:
        return 0.0
    increments = np.diff(distance)
    return float(np.sum(increments[increments > 0.0]))


def time_local_dephasing_rate(times_s: np.ndarray, coherence_abs: np.ndarray) -> np.ndarray:
    """Return gamma_eff(t) = - d log C(t) / dt."""

    times = np.asarray(times_s, dtype=float)
    values = np.asarray(coherence_abs, dtype=float)
    if times.shape != values.shape:
        raise ValueError("times_s and coherence_abs must have the same shape")
    clipped = np.clip(values, 1e-12, None)
    return -np.gradient(np.log(clipped), times)


def echo_boost_area(
    times_s: np.ndarray,
    echo_coherence: np.ndarray,
    markovian_prediction: np.ndarray,
) -> tuple[float, float]:
    """Return integrated and maximum echo excess over a Markovian prediction."""

    times = np.asarray(times_s, dtype=float)
    boost = np.asarray(echo_coherence, dtype=float) - np.asarray(markovian_prediction, dtype=float)
    positive = np.clip(boost, 0.0, None)
    return float(np.trapezoid(positive, times)), float(np.max(positive))


def memory_witness(
    times_s: np.ndarray,
    trace_distance: np.ndarray,
    echo_coherence: np.ndarray,
    markovian_echo_prediction: np.ndarray,
) -> MemoryWitness:
    rates = time_local_dephasing_rate(times_s, trace_distance)
    area, max_boost = echo_boost_area(times_s, echo_coherence, markovian_echo_prediction)
    return MemoryWitness(
        blp_measure=blp_information_backflow(times_s, trace_distance),
        negative_rate_fraction=float(np.mean(rates < -1e-9)),
        min_time_local_rate_s=float(np.min(rates)),
        echo_boost_area_s=area,
        max_echo_boost=max_boost,
    )
