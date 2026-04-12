from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PulseSequence:
    name: str
    total_time_s: float
    pulse_times_s: np.ndarray


def ramsey_sequence(total_time_s: float) -> PulseSequence:
    return PulseSequence("Ramsey", float(total_time_s), np.array([], dtype=float))


def hahn_echo_sequence(total_time_s: float) -> PulseSequence:
    return PulseSequence("Hahn echo", float(total_time_s), np.array([0.5 * float(total_time_s)], dtype=float))


def cpmg_sequence(total_time_s: float, n_pulses: int) -> PulseSequence:
    if n_pulses < 0:
        raise ValueError("n_pulses must be non-negative")
    pulse_times = (np.arange(int(n_pulses), dtype=float) + 0.5) * float(total_time_s) / max(int(n_pulses), 1)
    if n_pulses == 0:
        pulse_times = np.array([], dtype=float)
    return PulseSequence(f"CPMG-{int(n_pulses)}", float(total_time_s), pulse_times)


def udd_sequence(total_time_s: float, n_pulses: int) -> PulseSequence:
    if n_pulses < 0:
        raise ValueError("n_pulses must be non-negative")
    indices = np.arange(1, int(n_pulses) + 1, dtype=float)
    pulse_times = float(total_time_s) * np.sin(np.pi * indices / (2.0 * (int(n_pulses) + 1))) ** 2
    return PulseSequence(f"UDD-{int(n_pulses)}", float(total_time_s), pulse_times)


def switching_function(times_s: np.ndarray, sequence: PulseSequence) -> np.ndarray:
    times = np.asarray(times_s, dtype=float)
    pulse_times = np.sort(np.asarray(sequence.pulse_times_s, dtype=float))
    counts = np.searchsorted(pulse_times, times, side="right")
    return np.where(counts % 2 == 0, 1.0, -1.0)


def filter_function(
    omega_rad_s: np.ndarray,
    sequence: PulseSequence,
    n_time_samples: int = 4096,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    times = np.linspace(0.0, sequence.total_time_s, int(n_time_samples))
    y_t = switching_function(times, sequence)
    phase = np.exp(1j * omega[:, None] * times[None, :])
    integral = np.trapezoid(y_t[None, :] * phase, times, axis=1)
    return np.abs(integral) ** 2


def lorentzian_noise_spectrum(
    omega_rad_s: np.ndarray,
    amplitude: float,
    correlation_time_s: float,
    center_rad_s: float = 0.0,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    tau = float(correlation_time_s)
    if tau <= 0.0:
        raise ValueError("correlation_time_s must be positive")
    return float(amplitude) * tau / (1.0 + ((omega - float(center_rad_s)) * tau) ** 2)


def gaussian_noise_peak(
    omega_rad_s: np.ndarray,
    amplitude: float,
    center_rad_s: float,
    width_rad_s: float,
) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    width = float(width_rad_s)
    if width <= 0.0:
        raise ValueError("width_rad_s must be positive")
    return float(amplitude) * np.exp(-0.5 * ((omega - float(center_rad_s)) / width) ** 2)


def composite_noise_spectrum(omega_rad_s: np.ndarray) -> np.ndarray:
    omega = np.asarray(omega_rad_s, dtype=float)
    low_frequency = lorentzian_noise_spectrum(omega, amplitude=1.0e6, correlation_time_s=1.2e-3)
    narrow_peak = gaussian_noise_peak(
        omega,
        amplitude=2.4e-2,
        center_rad_s=2.0 * np.pi * 4.0e3,
        width_rad_s=2.0 * np.pi * 0.45e3,
    )
    return low_frequency + narrow_peak


def dephasing_exponent(
    omega_rad_s: np.ndarray,
    spectrum: np.ndarray,
    sequence: PulseSequence,
    n_time_samples: int = 4096,
) -> float:
    omega = np.asarray(omega_rad_s, dtype=float)
    spec = np.asarray(spectrum, dtype=float)
    filt = filter_function(omega, sequence, n_time_samples=n_time_samples)
    integrand = spec * filt / np.pi
    return float(np.trapezoid(integrand, omega))


def coherence_from_filter(
    omega_rad_s: np.ndarray,
    spectrum: np.ndarray,
    sequence: PulseSequence,
    n_time_samples: int = 4096,
) -> float:
    chi = dephasing_exponent(omega_rad_s, spectrum, sequence, n_time_samples=n_time_samples)
    return float(np.exp(-chi))


def filter_peak_frequency(
    omega_rad_s: np.ndarray,
    sequence: PulseSequence,
    n_time_samples: int = 4096,
) -> float:
    filt = filter_function(omega_rad_s, sequence, n_time_samples=n_time_samples)
    idx = int(np.argmax(filt))
    return float(np.asarray(omega_rad_s, dtype=float)[idx])


def sequence_family(total_time_s: float) -> tuple[PulseSequence, ...]:
    return (
        ramsey_sequence(total_time_s),
        hahn_echo_sequence(total_time_s),
        cpmg_sequence(total_time_s, 2),
        cpmg_sequence(total_time_s, 4),
        cpmg_sequence(total_time_s, 8),
        udd_sequence(total_time_s, 4),
        udd_sequence(total_time_s, 8),
    )
