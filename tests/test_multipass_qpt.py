from __future__ import annotations

import numpy as np

from oqs_control.hardware.multipass_qpt import (
    MultipassQPTConfig,
    estimate_single_process_from_multipass,
    ideal_input_stokes,
    matrix_root_near_identity,
    ptm_frobenius_error,
    run_multipass_monte_carlo,
    simulate_qpt_estimate,
    single_qubit_process,
    unitary_to_ptm,
    rotation_unitary,
)


def test_unitary_to_ptm_preserves_identity_row_for_x_rotation() -> None:
    ptm = unitary_to_ptm(rotation_unitary("x", np.pi / 2.0))

    assert np.allclose(ptm[0], [1.0, 0.0, 0.0, 0.0], atol=1e-12)
    assert np.isclose(np.linalg.det(ptm[1:, 1:]), 1.0)


def test_matrix_root_near_identity_recovers_powered_error() -> None:
    error = np.eye(4)
    error[1, 1] = 0.98
    error[2, 2] = 0.97
    error[3, 3] = 0.99
    powered = np.linalg.matrix_power(error, 5)
    recovered = matrix_root_near_identity(powered, 5)

    assert np.allclose(recovered, error, atol=1e-10)


def test_multipass_root_is_exact_without_spam_or_shot_noise() -> None:
    target, actual = single_qubit_process()
    measured_power = np.linalg.matrix_power(actual, 3)
    estimated = estimate_single_process_from_multipass(measured_power, target, passes=3)

    assert ptm_frobenius_error(estimated, actual) < 1e-10


def test_single_qpt_estimate_has_correct_shape() -> None:
    _, actual = single_qubit_process()
    config = MultipassQPTConfig(shots=10_000, readout_scale=1.0, prep_shrink=1.0)
    rng = np.random.default_rng(123)
    estimated = simulate_qpt_estimate(actual, 1, config, rng)

    assert estimated.shape == (4, 4)
    assert np.allclose(estimated[0], [1.0, 0.0, 0.0, 0.0])
    assert ideal_input_stokes().shape == (4, 4)


def test_multipass_monte_carlo_returns_improvement_factors() -> None:
    _, _, result = run_multipass_monte_carlo(
        passes=(2, 3),
        shots=256,
        seeds=(1, 2, 3),
    )

    assert result.single_errors.shape == (3,)
    assert set(result.multipass_errors) == {2, 3}
    assert all(value > 0.0 for value in result.improvement_factors.values())
