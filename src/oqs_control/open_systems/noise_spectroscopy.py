from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import nnls

from .noise_filtering import PulseSequence, dephasing_exponent, filter_function


@dataclass(frozen=True)
class SpectrumReconstruction:
    omega_rad_s: np.ndarray
    true_spectrum: np.ndarray
    reconstructed_spectrum: np.ndarray
    measured_coherence: np.ndarray
    predicted_coherence: np.ndarray
    chi_measured: np.ndarray
    residual_norm: float
    relative_error: float
    correlation: float


@dataclass(frozen=True)
class PeakSpectrumPoint:
    sequence: str
    pulse_count: int
    frequency_hz: float
    spectrum_estimate: float
    coherence: float
    chi: float


def colored_noise_spectrum(
    omega_rad_s: np.ndarray,
    amplitude: float = 3.2e-4,
    alpha: float = 0.85,
    reference_hz: float = 1.0e3,
    white_floor: float = 1.5e-7,
    peak_amplitude: float = 2.2e-4,
    peak_center_hz: float = 6.0e3,
    peak_width_hz: float = 0.8e3,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    freq_hz = np.maximum(omega / (2.0 * np.pi), 1e-12)
    base = float(amplitude) * (float(reference_hz) / freq_hz) ** float(alpha)
    peak = float(peak_amplitude) * np.exp(
        -0.5 * ((freq_hz - float(peak_center_hz)) / float(peak_width_hz)) ** 2
    )
    return base + float(white_floor) + peak


def flux_qubit_like_spectrum(
    omega_rad_s: np.ndarray,
    amplitude: float = 2.5e-9,
    alpha: float = 0.78,
    reference_hz: float = 1.0e6,
    white_floor: float = 1.8e-10,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    freq_hz = np.maximum(omega / (2.0 * np.pi), 1e-12)
    return float(amplitude) * (float(reference_hz) / freq_hz) ** float(alpha) + float(white_floor)


def filter_matrix(
    omega_rad_s: np.ndarray,
    sequences: tuple[PulseSequence, ...],
    n_time_samples: int = 2048,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    rows = []
    for sequence in sequences:
        filt = filter_function(omega, sequence, n_time_samples=n_time_samples)
        rows.append(filt / np.pi)
    return np.asarray(rows, dtype=float)


def simulate_coherences(
    omega_rad_s: np.ndarray,
    spectrum: np.ndarray,
    sequences: tuple[PulseSequence, ...],
    n_time_samples: int = 2048,
) -> tuple[np.ndarray, np.ndarray]:
    omega = np.asarray(omega_rad_s, dtype=float)
    spec = np.asarray(spectrum, dtype=float)
    chi_values = []
    for sequence in sequences:
        chi_values.append(dephasing_exponent(omega, spec, sequence, n_time_samples=n_time_samples))
    chi = np.asarray(chi_values, dtype=float)
    return np.exp(-chi), chi


def add_coherence_noise(
    coherence: np.ndarray,
    noise_std: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    values = np.asarray(coherence, dtype=float)
    noisy = values + rng.normal(scale=float(noise_std), size=values.shape)
    return np.clip(noisy, 1e-9, 1.0)


def _second_difference_matrix(size: int) -> np.ndarray:
    if size < 3:
        return np.zeros((0, size), dtype=float)
    matrix = np.zeros((size - 2, size), dtype=float)
    for idx in range(size - 2):
        matrix[idx, idx] = 1.0
        matrix[idx, idx + 1] = -2.0
        matrix[idx, idx + 2] = 1.0
    return matrix


def reconstruct_spectrum_nnls(
    omega_rad_s: np.ndarray,
    sequences: tuple[PulseSequence, ...],
    measured_coherence: np.ndarray,
    smoothness: float = 5e-3,
    n_time_samples: int = 2048,
    true_spectrum: np.ndarray | None = None,
) -> SpectrumReconstruction:
    omega = np.asarray(omega_rad_s, dtype=float)
    measured = np.clip(np.asarray(measured_coherence, dtype=float), 1e-12, 1.0)
    chi_measured = -np.log(measured)
    design = filter_matrix(omega, sequences, n_time_samples=n_time_samples)
    weights = np.gradient(omega)
    weighted_design = design * weights[None, :]

    if smoothness > 0.0:
        regularizer = float(smoothness) * _second_difference_matrix(omega.size)
        augmented_a = np.vstack([weighted_design, regularizer])
        augmented_b = np.concatenate([chi_measured, np.zeros(regularizer.shape[0])])
    else:
        augmented_a = weighted_design
        augmented_b = chi_measured

    reconstructed, residual = nnls(augmented_a, augmented_b)
    predicted_chi = weighted_design @ reconstructed
    predicted_coherence = np.exp(-predicted_chi)
    reference = np.asarray(true_spectrum if true_spectrum is not None else reconstructed, dtype=float)
    relative_error = float(np.linalg.norm(reconstructed - reference) / max(np.linalg.norm(reference), 1e-15))
    if np.std(reference) <= 0.0 or np.std(reconstructed) <= 0.0:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(reference, reconstructed)[0, 1])
    return SpectrumReconstruction(
        omega_rad_s=omega,
        true_spectrum=reference,
        reconstructed_spectrum=reconstructed,
        measured_coherence=measured,
        predicted_coherence=predicted_coherence,
        chi_measured=chi_measured,
        residual_norm=float(residual),
        relative_error=relative_error,
        correlation=correlation,
    )


def peak_approximation_points(
    omega_rad_s: np.ndarray,
    spectrum: np.ndarray,
    sequences: tuple[PulseSequence, ...],
    n_time_samples: int = 2048,
) -> tuple[PeakSpectrumPoint, ...]:
    omega = np.asarray(omega_rad_s, dtype=float)
    spec = np.asarray(spectrum, dtype=float)
    rows: list[PeakSpectrumPoint] = []
    coherences, chi_values = simulate_coherences(omega, spec, sequences, n_time_samples=n_time_samples)
    weights = np.gradient(omega)
    for sequence, coherence, chi in zip(sequences, coherences, chi_values):
        filt = filter_function(omega, sequence, n_time_samples=n_time_samples)
        area = float(np.sum(filt * weights) / np.pi)
        idx = int(np.argmax(filt))
        estimate = float(chi / max(area, 1e-30))
        rows.append(
            PeakSpectrumPoint(
                sequence=sequence.name,
                pulse_count=int(len(sequence.pulse_times_s)),
                frequency_hz=float(omega[idx] / (2.0 * np.pi)),
                spectrum_estimate=estimate,
                coherence=float(coherence),
                chi=float(chi),
            )
        )
    return tuple(rows)


def fit_power_law_from_points(points: tuple[PeakSpectrumPoint, ...]) -> dict[str, float]:
    freq = np.array([point.frequency_hz for point in points if point.frequency_hz > 0.0], dtype=float)
    spec = np.array([point.spectrum_estimate for point in points if point.frequency_hz > 0.0], dtype=float)
    mask = spec > 0.0
    if np.count_nonzero(mask) < 2:
        return {"amplitude_at_1mhz": float("nan"), "alpha": float("nan"), "rmse_log": float("nan")}
    x = np.log(freq[mask] / 1.0e6)
    y = np.log(spec[mask])
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    return {
        "amplitude_at_1mhz": float(np.exp(intercept)),
        "alpha": float(-slope),
        "rmse_log": float(np.sqrt(np.mean((y - fitted) ** 2))),
    }
