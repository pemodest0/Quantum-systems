from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .io import TecmagTNTData, read_tnt


@dataclass(frozen=True)
class TransitionAmplitudeEstimate:
    label: str
    target_freq_hz: float
    measured_freq_hz: float
    complex_amplitude: complex
    integrated_magnitude: float
    phase_rad: float


def fft_spectrum(signal: np.ndarray, dwell_time: float) -> tuple[np.ndarray, np.ndarray]:
    spectrum = np.fft.fftshift(np.fft.fft(signal))
    freq_hz = np.fft.fftshift(np.fft.fftfreq(signal.size, d=dwell_time))
    return freq_hz, spectrum


def apply_exponential_apodization(
    signal: np.ndarray, dwell_time: float, line_broadening_hz: float
) -> np.ndarray:
    if line_broadening_hz <= 0:
        return np.array(signal, copy=True)
    time_s = np.arange(signal.size, dtype=float) * dwell_time
    return signal * np.exp(-np.pi * line_broadening_hz * time_s)


def fft_spectrum_processed(
    signal: np.ndarray,
    dwell_time: float,
    zero_fill_factor: int = 1,
    line_broadening_hz: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    processed = apply_exponential_apodization(signal, dwell_time, line_broadening_hz)
    n_fft = max(signal.size, int(signal.size * zero_fill_factor))
    spectrum = np.fft.fftshift(np.fft.fft(processed, n=n_fft))
    freq_hz = np.fft.fftshift(np.fft.fftfreq(n_fft, d=dwell_time))
    return freq_hz, spectrum


def fixed_window_complex_amplitude(
    spectrum: np.ndarray,
    freq_hz: np.ndarray,
    center_hz: float,
    window_hz: float,
) -> complex:
    mask = np.abs(freq_hz - center_hz) <= (window_hz / 2.0)
    if not np.any(mask):
        return 0.0 + 0.0j
    local_freq = freq_hz[mask]
    local_spec = spectrum[mask]
    sigma = max(window_hz / 6.0, float(np.mean(np.diff(freq_hz))) * 2.0)
    weights = np.exp(-0.5 * ((local_freq - center_hz) / sigma) ** 2)
    return np.sum(weights * local_spec) / np.sum(weights)


def extract_transition_amplitudes(
    signal: np.ndarray,
    dwell_time: float,
    centers_hz: np.ndarray,
    labels: tuple[str, ...] | list[str] | None = None,
    zero_fill_factor: int = 4,
    line_broadening_hz: float = 0.0,
    integration_window_hz: float = 800.0,
    diagnostic_search_hz: float = 1500.0,
) -> tuple[np.ndarray, np.ndarray, list[TransitionAmplitudeEstimate]]:
    freq_hz, spectrum = fft_spectrum_processed(
        signal,
        dwell_time=dwell_time,
        zero_fill_factor=zero_fill_factor,
        line_broadening_hz=line_broadening_hz,
    )

    if labels is None:
        labels = tuple(f"line_{idx}" for idx in range(len(centers_hz)))

    estimates: list[TransitionAmplitudeEstimate] = []
    for label, center_hz in zip(labels, centers_hz):
        amplitude = fixed_window_complex_amplitude(
            spectrum=spectrum,
            freq_hz=freq_hz,
            center_hz=float(center_hz),
            window_hz=integration_window_hz,
        )

        diagnostic_mask = np.abs(freq_hz - center_hz) <= diagnostic_search_hz
        if np.any(diagnostic_mask):
            local_freq = freq_hz[diagnostic_mask]
            local_spec = spectrum[diagnostic_mask]
            peak_idx = int(np.argmax(np.abs(local_spec)))
            measured_freq_hz = float(local_freq[peak_idx])
        else:
            measured_freq_hz = float(center_hz)

        estimates.append(
            TransitionAmplitudeEstimate(
                label=str(label),
                target_freq_hz=float(center_hz),
                measured_freq_hz=measured_freq_hz,
                complex_amplitude=complex(amplitude),
                integrated_magnitude=float(abs(amplitude)),
                phase_rad=float(np.angle(amplitude)),
            )
        )

    return freq_hz, spectrum, estimates


def dominant_peaks(
    spectrum: np.ndarray,
    freq_hz: np.ndarray,
    limit: int = 8,
    exclusion_bins: int = 20,
) -> list[dict[str, float]]:
    magnitude = np.abs(spectrum)
    order = np.argsort(magnitude)[::-1]
    used = np.zeros_like(magnitude, dtype=bool)
    peaks: list[dict[str, float]] = []

    for idx in order:
        if used[idx]:
            continue

        peaks.append(
            {
                "freq_hz": float(freq_hz[idx]),
                "magnitude": float(magnitude[idx]),
            }
        )

        start = max(0, idx - exclusion_bins)
        stop = min(magnitude.size, idx + exclusion_bins + 1)
        used[start:stop] = True

        if len(peaks) >= limit:
            break

    return peaks


def flatten_first_trace(tnt_data: TecmagTNTData) -> np.ndarray:
    return tnt_data.raw_data[:, 0, 0, 0]


def summarize_reference(path: str | Path) -> dict[str, object]:
    tnt_data = read_tnt(path)
    fid = flatten_first_trace(tnt_data)
    freq_hz, spectrum = fft_spectrum(fid, dwell_time=8e-6)

    return {
        "path": str(tnt_data.path),
        "magic_ascii": tnt_data.header.magic_ascii,
        "date_raw": tnt_data.header.date_raw,
        "npoints1d": tnt_data.header.npoints1d,
        "acqpoints": tnt_data.acqpoints,
        "scans1d": tnt_data.header.scans1d,
        "actualscan1d": tnt_data.actualscan1d,
        "dominant_peaks": dominant_peaks(spectrum, freq_hz),
    }
