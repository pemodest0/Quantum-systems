from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr.relaxation_models import (
    QuadrupolarRelaxationParams,
    fit_redfield_effective_to_envelopes,
    phenomenological_transition_envelopes,
    redfield_effective_envelopes,
    redfield_inspired_rates,
    reduced_spectral_densities,
)


def test_reduced_spectral_density_peak_tracks_larmor_timescale() -> None:
    larmor_hz = 105.7507331e6
    tau_grid = np.logspace(-12, -6, 500)
    densities = reduced_spectral_densities(tau_grid, larmor_hz)

    omega0 = 2.0 * np.pi * larmor_hz
    tau_peak = float(tau_grid[int(np.argmax(densities.j1_s))])

    assert np.all(densities.j0_s > 0.0)
    assert np.all(densities.j1_s > 0.0)
    assert np.all(densities.j2_s > 0.0)
    assert 0.75 / omega0 < tau_peak < 1.35 / omega0


def test_redfield_rates_are_positive_and_scale_quadratically_with_coupling() -> None:
    tau_c_s = 2e-9
    rates_a = redfield_inspired_rates(
        tau_c_s,
        QuadrupolarRelaxationParams(quadrupolar_coupling_hz=2_000.0),
    )
    rates_b = redfield_inspired_rates(
        tau_c_s,
        QuadrupolarRelaxationParams(quadrupolar_coupling_hz=4_000.0),
    )

    assert float(rates_a.r2_central) > 0.0
    assert float(rates_a.r2_satellite) > 0.0
    assert np.isclose(float(rates_b.r2_central / rates_a.r2_central), 4.0)


def test_redfield_envelopes_are_normalized_and_decay() -> None:
    time_s = np.linspace(0.0, 0.02, 100)
    rates = redfield_inspired_rates(
        1e-7,
        QuadrupolarRelaxationParams(quadrupolar_coupling_hz=2_000.0),
    )
    envelopes = redfield_effective_envelopes(time_s, rates)

    assert envelopes.shape == (time_s.size, 3)
    assert np.allclose(envelopes[0], 1.0)
    assert np.all(envelopes[-1] < envelopes[0])


def test_redfield_grid_fit_returns_finite_effective_parameters() -> None:
    time_s = np.linspace(0.0, 0.005, 120)
    target = phenomenological_transition_envelopes(time_s)
    result = fit_redfield_effective_to_envelopes(
        time_s=time_s,
        target_envelopes=target,
        larmor_hz=105.7507331e6,
        tau_grid_s=np.logspace(-10, -6, 8),
        coupling_grid_hz=np.logspace(2, 4, 8),
    )

    assert result.tau_c_s > 0.0
    assert result.quadrupolar_coupling_hz > 0.0
    assert np.isfinite(result.rmse)
