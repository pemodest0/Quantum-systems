from __future__ import annotations

from pathlib import Path

import numpy as np

from oqs_control.platforms.na23_nmr import (
    NMRConfig,
    NMRDissipationRates,
    effective_jump_operators,
    fit_reference_dissipative_rates,
    run_synthetic_dissipative_recovery,
    run_synthetic_validation_suite,
    simulate_open_reference_experiment,
)


def test_effective_jump_operators_are_dimensionally_consistent() -> None:
    config = NMRConfig(n_acq=64, n_zf=64)
    jumps = effective_jump_operators(
        config,
        NMRDissipationRates(gamma_phi=100.0, gamma_relax=30.0),
    )

    assert len(jumps) == 7
    assert all(jump.shape == (config.dim, config.dim) for jump in jumps)


def test_open_nmr_simulation_preserves_physical_state_constraints() -> None:
    result = simulate_open_reference_experiment(
        NMRConfig(n_acq=96, n_zf=96),
        rates=NMRDissipationRates(gamma_phi=120.0, gamma_relax=25.0),
        n_points=96,
    )

    assert result.fid.shape == (96,)
    assert result.states.shape == (96, 4, 4)
    assert result.checks.max_trace_error < 1e-10
    assert result.checks.max_hermiticity_error < 1e-10
    assert result.checks.min_eigenvalue > -1e-10
    assert np.all(np.isfinite(result.purity))
    assert np.all(np.isfinite(result.entropy))


def test_synthetic_dissipative_recovery_recovers_known_rates() -> None:
    result = run_synthetic_dissipative_recovery(
        config=NMRConfig(n_acq=96, n_zf=96),
        true_rates=NMRDissipationRates(gamma_phi=180.0, gamma_relax=40.0),
        initial_rates=NMRDissipationRates(gamma_phi=80.0, gamma_relax=15.0),
        n_points=96,
    )

    assert result.success
    assert result.relative_error_gamma_phi < 1e-4
    assert result.relative_error_gamma_relax < 1e-4


def test_synthetic_validation_suite_summarizes_cases() -> None:
    suite = run_synthetic_validation_suite(
        config=NMRConfig(n_acq=64, n_zf=64),
        true_rates=NMRDissipationRates(gamma_phi=160.0, gamma_relax=35.0),
        initial_rates=NMRDissipationRates(gamma_phi=80.0, gamma_relax=15.0),
        n_points=64,
        noise_levels=(0.0,),
        random_seeds=(7,),
    )

    assert suite.total_count == 1
    assert suite.success_count == 1
    assert suite.max_relative_error_gamma_phi < 1e-4
    assert suite.max_relative_error_gamma_relax < 1e-4


def test_reference_dissipative_fit_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = fit_reference_dissipative_rates(
        root / "data" / "reference" / "Referential2.tnt",
        initial_rates=NMRDissipationRates(gamma_phi=160.0, gamma_relax=35.0),
        n_points=64,
    )

    assert result.success
    assert result.n_points == 64
    assert np.isfinite(result.normalized_rmse_fid)
    assert result.fitted_rates.gamma_phi > 0
    assert result.fitted_rates.gamma_relax > 0
    assert result.fitted.checks.max_trace_error < 1e-10
