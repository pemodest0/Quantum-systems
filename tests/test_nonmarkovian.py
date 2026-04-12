from __future__ import annotations

import numpy as np

from oqs_control.open_systems.nonmarkovian import (
    blp_information_backflow,
    damped_revival_coherence,
    fit_markovian_dephasing,
    markovian_dephasing_coherence,
    memory_witness,
    quasi_static_echo_coherence,
    quasi_static_ramsey_coherence,
    time_local_dephasing_rate,
)


def test_markovian_dephasing_is_monotonic_and_has_zero_blp_backflow() -> None:
    times = np.linspace(0.0, 0.01, 200)
    coherence = markovian_dephasing_coherence(times, gamma_s=250.0)

    assert np.all(np.diff(coherence) <= 1e-12)
    assert blp_information_backflow(times, coherence) == 0.0
    assert np.all(time_local_dephasing_rate(times, coherence) > 0.0)


def test_revival_coherence_has_positive_information_backflow() -> None:
    times = np.linspace(0.0, 0.012, 500)
    coherence = damped_revival_coherence(times, gamma_s=80.0, omega_rad_s=2.0 * np.pi * 380.0)

    assert blp_information_backflow(times, coherence) > 0.05
    assert np.min(time_local_dephasing_rate(times, coherence)) < 0.0


def test_quasi_static_echo_exceeds_markovian_fit_prediction() -> None:
    times = np.linspace(0.0, 0.012, 250)
    ramsey = quasi_static_ramsey_coherence(times, sigma_rad_s=360.0)
    fit = fit_markovian_dephasing(times, ramsey)
    echo = quasi_static_echo_coherence(times, sigma_rad_s=360.0, refocusing_efficiency=0.94)

    assert fit.gamma_s > 0.0
    assert echo[-1] > fit.fitted[-1]


def test_memory_witness_collects_failure_signatures() -> None:
    times = np.linspace(0.0, 0.012, 500)
    trace_distance = damped_revival_coherence(times, gamma_s=80.0, omega_rad_s=2.0 * np.pi * 380.0)
    ramsey = quasi_static_ramsey_coherence(times, sigma_rad_s=360.0)
    fit = fit_markovian_dephasing(times, ramsey)
    echo = quasi_static_echo_coherence(times, sigma_rad_s=360.0, refocusing_efficiency=0.94)
    witness = memory_witness(times, trace_distance, echo, fit.fitted)

    assert witness.blp_measure > 0.0
    assert witness.negative_rate_fraction > 0.0
    assert witness.max_echo_boost > 0.0
