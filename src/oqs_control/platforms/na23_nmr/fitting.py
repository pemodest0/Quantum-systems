from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from .analysis import flatten_first_trace
from .config import NMRConfig
from .io import read_tnt
from .simulation import simulate_fid


@dataclass(frozen=True)
class SpectralFitResult:
    success: bool
    message: str
    cost: float
    nfev: int
    nu_q_hz: float
    t_pi2_us: float
    line_broadening_hz: float
    fit_window_hz: float
    zero_fill_factor: int
    fitted_config: NMRConfig
    freq_hz: np.ndarray
    reference_magnitude: np.ndarray
    fitted_magnitude: np.ndarray


def exponential_apodization(
    fid: np.ndarray, dwell_time: float, line_broadening_hz: float
) -> np.ndarray:
    if line_broadening_hz <= 0:
        return np.array(fid, copy=True)
    time_s = np.arange(fid.size, dtype=float) * dwell_time
    return fid * np.exp(-np.pi * line_broadening_hz * time_s)


def magnitude_spectrum(
    fid: np.ndarray, dwell_time: float, zero_fill: int
) -> tuple[np.ndarray, np.ndarray]:
    spectrum = np.fft.fftshift(np.fft.fft(fid, n=zero_fill))
    freq_hz = np.fft.fftshift(np.fft.fftfreq(zero_fill, d=dwell_time))
    return freq_hz, np.abs(spectrum)


def _normalize(values: np.ndarray) -> np.ndarray:
    peak = np.max(values)
    if peak <= 0:
        return values
    return values / peak


def _window_mask(freq_hz: np.ndarray, fit_window_hz: float) -> np.ndarray:
    return np.abs(freq_hz) <= fit_window_hz


def fit_reference_spectrum(
    reference_path: str | Path,
    initial_config: NMRConfig | None = None,
    fit_window_hz: float = 30000.0,
    zero_fill_factor: int = 4,
) -> SpectralFitResult:
    base = initial_config or NMRConfig()
    tnt_data = read_tnt(reference_path)
    ref_fid = flatten_first_trace(tnt_data)
    zero_fill = zero_fill_factor * ref_fid.size

    ref_freq_hz, ref_mag_full = magnitude_spectrum(ref_fid, base.dwell_time, zero_fill)
    mask = _window_mask(ref_freq_hz, fit_window_hz)
    ref_mag = _normalize(ref_mag_full[mask])
    weights = 0.25 + ref_mag

    x0 = np.array([base.nu_q, base.t_pi2 * 1e6, 80.0], dtype=float)
    lower = np.array([12000.0, 2.0, 0.0], dtype=float)
    upper = np.array([20000.0, 8.0, 800.0], dtype=float)

    def residual(theta: np.ndarray) -> np.ndarray:
        nu_q_hz, t_pi2_us, lb_hz = theta
        config = base.clone_with(nu_q=nu_q_hz, t_pi2=t_pi2_us * 1e-6)
        sim_fid = simulate_fid(config)
        sim_fid = exponential_apodization(sim_fid, config.dwell_time, lb_hz)
        sim_freq_hz, sim_mag_full = magnitude_spectrum(sim_fid, config.dwell_time, zero_fill)
        sim_mag = _normalize(sim_mag_full[_window_mask(sim_freq_hz, fit_window_hz)])
        return np.sqrt(weights) * (sim_mag - ref_mag)

    opt = least_squares(
        residual,
        x0=x0,
        bounds=(lower, upper),
        x_scale=np.array([1000.0, 1.0, 100.0]),
        max_nfev=50,
    )

    nu_q_hz, t_pi2_us, lb_hz = opt.x
    fitted_config = base.clone_with(nu_q=nu_q_hz, t_pi2=t_pi2_us * 1e-6)
    fitted_fid = simulate_fid(fitted_config)
    fitted_fid = exponential_apodization(fitted_fid, fitted_config.dwell_time, lb_hz)
    fit_freq_hz, fit_mag_full = magnitude_spectrum(
        fitted_fid, fitted_config.dwell_time, zero_fill
    )

    return SpectralFitResult(
        success=bool(opt.success),
        message=str(opt.message),
        cost=float(opt.cost),
        nfev=int(opt.nfev),
        nu_q_hz=float(nu_q_hz),
        t_pi2_us=float(t_pi2_us),
        line_broadening_hz=float(lb_hz),
        fit_window_hz=float(fit_window_hz),
        zero_fill_factor=int(zero_fill_factor),
        fitted_config=fitted_config,
        freq_hz=ref_freq_hz[mask],
        reference_magnitude=ref_mag,
        fitted_magnitude=_normalize(fit_mag_full[_window_mask(fit_freq_hz, fit_window_hz)]),
    )
