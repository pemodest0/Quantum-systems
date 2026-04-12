from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr import NMRConfig
from oqs_control.platforms.na23_nmr.grape_control import (
    ControlEnsembleMember,
    dephase_in_measurement_basis,
    optimize_unitary_grape,
    prepare_state_with_dephasing,
    propagate_controls,
    rectangular_controls,
    target_pseudo_pure_from_deviation,
    thermal_deviation_state_from_iz,
    unitary_fidelity,
    unitary_fidelity_and_gradient,
)
from oqs_control.platforms.na23_nmr.quadrupolar_qip import deviation_fidelity
from oqs_control.platforms.na23_nmr.selective_pulses import (
    ideal_selective_rotation,
    selected_transition_frame_hamiltonian,
)


def test_unitary_grape_gradient_matches_finite_difference() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    pair = config.transition_pairs[1]
    drift = selected_transition_frame_hamiltonian(config, pair)
    target = ideal_selective_rotation(config.dim, pair, np.pi / 3.0)
    controls = np.array(
        [
            [1.0e3, -0.7e3],
            [0.4e3, 0.9e3],
            [-0.5e3, 0.2e3],
        ],
        dtype=float,
    )
    ensemble = (ControlEnsembleMember(drift=drift),)

    fidelity, gradient = unitary_fidelity_and_gradient(
        controls.reshape(-1),
        target,
        ensemble,
        config.i_x,
        config.i_y,
        dt_s=5e-6,
    )
    step = 1e-3
    idx = 2
    plus = controls.reshape(-1).copy()
    minus = controls.reshape(-1).copy()
    plus[idx] += step
    minus[idx] -= step
    f_plus, _ = unitary_fidelity_and_gradient(
        plus,
        target,
        ensemble,
        config.i_x,
        config.i_y,
        dt_s=5e-6,
    )
    f_minus, _ = unitary_fidelity_and_gradient(
        minus,
        target,
        ensemble,
        config.i_x,
        config.i_y,
        dt_s=5e-6,
    )
    finite_difference = (f_plus - f_minus) / (2.0 * step)

    assert 0.0 <= fidelity <= 1.0
    assert np.isclose(gradient[idx], finite_difference, rtol=1e-4, atol=1e-7)


def test_short_grape_run_improves_unitary_fidelity() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    pair = config.transition_pairs[1]
    drift = selected_transition_frame_hamiltonian(config, pair)
    target = ideal_selective_rotation(config.dim, pair, np.pi)
    duration_s = 80e-6
    n_segments = 6
    controls0 = rectangular_controls(n_segments, duration_s, np.pi)
    result = optimize_unitary_grape(
        target,
        controls0,
        dt_s=duration_s / n_segments,
        ensemble=(ControlEnsembleMember(drift=drift),),
        control_x=config.i_x,
        control_y=config.i_y,
        max_amplitude_rad_s=2.0 * np.pi * 80e3,
        max_iter=4,
    )

    assert result.final_fidelity >= result.initial_fidelity


def test_dephase_after_control_keeps_valid_density_matrix() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    controls = np.zeros((3, 2), dtype=float)
    rho0 = thermal_deviation_state_from_iz(config.i_z, scale=0.03)
    prepared = prepare_state_with_dephasing(
        controls,
        dt_s=1e-6,
        drift=config.h_free,
        control_x=config.i_x,
        control_y=config.i_y,
        initial_state=rho0,
    )

    assert np.allclose(prepared, prepared.conj().T)
    assert np.isclose(np.trace(prepared), 1.0)
    assert np.min(np.linalg.eigvalsh(prepared).real) >= -1e-12
    assert np.allclose(prepared, dephase_in_measurement_basis(prepared))


def test_target_pseudo_pure_from_deviation_is_aligned_with_projector() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    rho0 = thermal_deviation_state_from_iz(config.i_z, scale=0.03)
    target = target_pseudo_pure_from_deviation(0, rho0)

    assert target[0, 0].real > target[1, 1].real
    assert target[0, 0].real > target[2, 2].real
    assert target[0, 0].real > target[3, 3].real
    assert deviation_fidelity(target, target) > 1.0 - 1e-12


def test_propagate_controls_zero_controls_matches_drift() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    controls = np.zeros((4, 2), dtype=float)
    dt_s = 2e-6
    actual = propagate_controls(controls, dt_s, config.h_free, config.i_x, config.i_y)
    expected = np.linalg.matrix_power(
        propagate_controls(controls[:1], dt_s, config.h_free, config.i_x, config.i_y),
        4,
    )

    assert unitary_fidelity(expected, actual) > 1.0 - 1e-12
