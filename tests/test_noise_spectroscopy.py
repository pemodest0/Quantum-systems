from __future__ import annotations

import numpy as np

from oqs_control.open_systems.noise_filtering import cpmg_sequence
from oqs_control.open_systems.noise_spectroscopy import (
    add_coherence_noise,
    colored_noise_spectrum,
    filter_matrix,
    fit_power_law_from_points,
    flux_qubit_like_spectrum,
    peak_approximation_points,
    reconstruct_spectrum_nnls,
    simulate_coherences,
)


def test_filter_matrix_has_expected_shape() -> None:
    omega = np.linspace(2.0 * np.pi * 100.0, 2.0 * np.pi * 5000.0, 100)
    sequences = tuple(cpmg_sequence(1e-3, count) for count in (1, 2, 4))
    matrix = filter_matrix(omega, sequences, n_time_samples=512)

    assert matrix.shape == (3, 100)
    assert np.all(matrix >= 0.0)


def test_coherence_noise_is_clipped_to_physical_range() -> None:
    coherence = np.array([0.1, 0.5, 0.9])
    noisy = add_coherence_noise(coherence, noise_std=2.0, seed=1)

    assert np.all(noisy >= 1e-9)
    assert np.all(noisy <= 1.0)


def test_nnls_reconstruction_returns_nonnegative_spectrum() -> None:
    omega = np.linspace(2.0 * np.pi * 200.0, 2.0 * np.pi * 12000.0, 140)
    spectrum = colored_noise_spectrum(omega)
    sequences = tuple(cpmg_sequence(1.2e-3, count) for count in range(1, 18))
    coherence, _ = simulate_coherences(omega, spectrum, sequences, n_time_samples=512)
    result = reconstruct_spectrum_nnls(
        omega,
        sequences,
        coherence,
        smoothness=2e-3,
        n_time_samples=512,
        true_spectrum=spectrum,
    )

    assert np.all(result.reconstructed_spectrum >= 0.0)
    assert result.correlation > 0.65


def test_peak_approximation_power_law_recovers_positive_alpha() -> None:
    omega = np.linspace(2.0 * np.pi * 0.1e6, 2.0 * np.pi * 12.0e6, 900)
    spectrum = flux_qubit_like_spectrum(omega, alpha=0.8)
    total_time = 4.0e-6
    sequences = tuple(cpmg_sequence(total_time, count) for count in (2, 4, 8, 16, 32))
    points = peak_approximation_points(omega, spectrum, sequences, n_time_samples=1024)
    fit = fit_power_law_from_points(points)

    assert fit["alpha"] > 0.0
    assert fit["rmse_log"] < 1.0
