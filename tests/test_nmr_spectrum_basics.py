from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr.analysis import apply_exponential_apodization
from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.simulation import simulate_reference_experiment


def local_peak_frequency(freq_hz: np.ndarray, spectrum: np.ndarray, center_hz: float, window_hz: float) -> float:
    mask = np.abs(freq_hz - center_hz) <= window_hz
    assert np.any(mask)
    local_freq = freq_hz[mask]
    local_mag = np.abs(spectrum[mask])
    return float(local_freq[int(np.argmax(local_mag))])


def test_reference_spectrum_has_expected_central_and_satellite_lines() -> None:
    config = NMRConfig(n_acq=2048, n_zf=2048)
    result = simulate_reference_experiment(config)

    assert abs(local_peak_frequency(result.freq_hz, result.spectrum, 0.0, 900.0)) < 125.0
    assert abs(local_peak_frequency(result.freq_hz, result.spectrum, config.nu_q, 900.0) - config.nu_q) < 125.0
    assert abs(local_peak_frequency(result.freq_hz, result.spectrum, -config.nu_q, 900.0) + config.nu_q) < 125.0


def test_satellite_position_tracks_nu_q_change() -> None:
    config = NMRConfig(n_acq=2048, n_zf=2048, nu_q=12000.0)
    result = simulate_reference_experiment(config)
    sat_plus = local_peak_frequency(result.freq_hz, result.spectrum, config.nu_q, 900.0)

    assert abs(sat_plus - config.nu_q) < 125.0


def test_exponential_apodization_reduces_fid_tail() -> None:
    config = NMRConfig(n_acq=512, n_zf=512)
    result = simulate_reference_experiment(config)
    apodized = apply_exponential_apodization(result.fid, config.dwell_time, line_broadening_hz=25.0)

    assert abs(apodized[-1]) < abs(result.fid[-1])
