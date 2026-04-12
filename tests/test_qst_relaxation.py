from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr import NMRConfig
from oqs_control.platforms.na23_nmr.qst_relaxation import (
    QSTRelaxationRates,
    coherent_superposition_state,
    estimate_rates_from_qst,
    mix_with_identity,
    population_biased_state,
    population_deviation_norms,
    reconstruct_qst_trajectory,
    synthetic_quadrupolar_relaxation_state,
    synthetic_relaxation_trajectory,
)


def test_synthetic_relaxation_preserves_density_matrix_properties() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    rho0 = coherent_superposition_state(config.dim)
    rho_t = synthetic_quadrupolar_relaxation_state(
        rho0,
        time_s=0.002,
        config=config,
        rates=QSTRelaxationRates(gamma_population=40.0, gamma_dephasing=20.0),
    )

    assert np.allclose(np.trace(rho_t), 1.0, atol=1e-12)
    assert np.allclose(rho_t, rho_t.conj().T, atol=1e-12)
    assert np.min(np.linalg.eigvalsh(rho_t)) > -1e-12


def test_population_deviation_decays_monotonically() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    times = np.linspace(0.0, 0.01, 12)
    states = synthetic_relaxation_trajectory(
        mix_with_identity(population_biased_state(config.dim)),
        times,
        config,
        QSTRelaxationRates(gamma_population=60.0, gamma_dephasing=30.0),
        include_unitary_phase=False,
    )
    norms = population_deviation_norms(states)

    assert np.all(np.diff(norms) <= 1e-12)


def test_qst_reconstruction_is_high_fidelity_without_noise() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    times = np.linspace(0.0, 0.003, 5)
    states = synthetic_relaxation_trajectory(
        mix_with_identity(coherent_superposition_state(config.dim)),
        times,
        config,
        QSTRelaxationRates(gamma_population=35.0, gamma_dephasing=15.0),
    )
    trajectory = reconstruct_qst_trajectory(
        "coherent",
        states,
        times,
        config,
        noise_std=0.0,
        random_seed=1,
    )

    assert float(np.min(trajectory.fidelities)) > 0.999
    assert float(np.max(trajectory.frobenius_errors)) < 1e-6


def test_rate_estimator_recovers_synthetic_rates_without_tomography_noise() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    rates = QSTRelaxationRates(gamma_population=50.0, gamma_dephasing=25.0)
    times = np.linspace(0.0, 0.012, 18)
    pop_states = synthetic_relaxation_trajectory(
        mix_with_identity(population_biased_state(config.dim)),
        times,
        config,
        rates,
        include_unitary_phase=False,
    )
    coh_states = synthetic_relaxation_trajectory(
        mix_with_identity(coherent_superposition_state(config.dim)),
        times,
        config,
        rates,
        include_unitary_phase=False,
    )
    pop_trajectory = reconstruct_qst_trajectory("population", pop_states, times, config)
    coh_trajectory = reconstruct_qst_trajectory("coherence", coh_states, times, config)
    estimate = estimate_rates_from_qst(pop_trajectory, coh_trajectory, config.m_vals)

    assert abs(estimate.gamma_population - rates.gamma_population) / rates.gamma_population < 0.05
    assert abs(estimate.gamma_dephasing - rates.gamma_dephasing) / rates.gamma_dephasing < 0.08
