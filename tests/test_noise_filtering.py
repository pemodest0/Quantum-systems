from __future__ import annotations

import numpy as np

from oqs_control.open_systems.noise_filtering import (
    coherence_from_filter,
    composite_noise_spectrum,
    cpmg_sequence,
    filter_function,
    filter_peak_frequency,
    hahn_echo_sequence,
    ramsey_sequence,
    switching_function,
    udd_sequence,
)


def test_switching_function_flips_at_echo_pulse() -> None:
    seq = hahn_echo_sequence(1.0)
    times = np.array([0.25, 0.75])
    values = switching_function(times, seq)

    assert np.allclose(values, [1.0, -1.0])


def test_filter_function_is_non_negative() -> None:
    omega = np.linspace(1.0, 1000.0, 200)
    filt = filter_function(omega, cpmg_sequence(1e-3, 2), n_time_samples=512)

    assert filt.shape == omega.shape
    assert np.all(filt >= 0.0)


def test_echo_filters_static_noise_better_than_ramsey() -> None:
    omega = np.linspace(1.0, 2.0 * np.pi * 8000.0, 600)
    spectrum = composite_noise_spectrum(omega)
    total_time = 1.2e-3
    ramsey = coherence_from_filter(omega, spectrum, ramsey_sequence(total_time), n_time_samples=1024)
    echo = coherence_from_filter(omega, spectrum, hahn_echo_sequence(total_time), n_time_samples=1024)

    assert echo > ramsey


def test_filter_peak_frequency_increases_with_cpmg_pulse_count() -> None:
    omega = np.linspace(1.0, 2.0 * np.pi * 20000.0, 900)
    peak_2 = filter_peak_frequency(omega, cpmg_sequence(1e-3, 2), n_time_samples=1024)
    peak_8 = filter_peak_frequency(omega, cpmg_sequence(1e-3, 8), n_time_samples=1024)

    assert peak_8 > peak_2


def test_udd_sequence_pulses_are_inside_interval() -> None:
    seq = udd_sequence(1.0, 4)

    assert np.all(seq.pulse_times_s > 0.0)
    assert np.all(seq.pulse_times_s < 1.0)
    assert np.all(np.diff(seq.pulse_times_s) > 0.0)
