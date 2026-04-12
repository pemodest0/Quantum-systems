from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .analysis import fft_spectrum
from .config import NMRConfig


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    fid: np.ndarray
    spectrum: np.ndarray
    freq_hz: np.ndarray


def biexponential_decay(params_row: np.ndarray, time_s: np.ndarray) -> np.ndarray:
    a1, rate1, a2, rate2 = params_row
    return a1 * np.exp(rate1 * time_s) + a2 * np.exp(rate2 * time_s)


def _apply_transition_decay(
    rho: np.ndarray, config: NMRConfig, time_s: float
) -> np.ndarray:
    rho_obs = rho.copy()
    for row_idx, (i, j) in enumerate(config.transition_pairs):
        decay = biexponential_decay(config.decay_params[row_idx], np.array([time_s]))[0]
        rho_obs[i, j] *= decay
        rho_obs[j, i] *= decay
    return rho_obs


def simulate_fid(
    config: NMRConfig,
    rho0: np.ndarray | None = None,
    n_points: int | None = None,
) -> np.ndarray:
    total_points = n_points or config.n_acq

    if rho0 is None:
        rho = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T
    else:
        rho = np.array(rho0, dtype=complex, copy=True)

    rho = config.u_dead @ rho @ config.u_dead.conj().T

    fid = np.zeros(total_points, dtype=complex)
    for idx in range(total_points):
        time_s = idx * config.dwell_time
        rho_obs = _apply_transition_decay(rho, config, time_s)
        fid[idx] = np.trace(rho_obs @ config.detector)
        rho = config.u_dwell @ rho @ config.u_dwell.conj().T

    # Match the MATLAB import convention, which conjugates Tecmag data.
    return np.conj(fid)


def simulate_reference_experiment(
    config: NMRConfig | None = None,
) -> SimulationResult:
    active = config or NMRConfig()
    fid = simulate_fid(active)
    freq_hz, spectrum = fft_spectrum(fid, active.dwell_time)
    time_s = np.arange(fid.size, dtype=float) * active.dwell_time
    return SimulationResult(
        time_s=time_s,
        fid=fid,
        spectrum=spectrum,
        freq_hz=freq_hz,
    )
