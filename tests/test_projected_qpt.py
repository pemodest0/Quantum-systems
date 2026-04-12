from __future__ import annotations

import numpy as np

from oqs_control.hardware.multipass_qpt import (
    MultipassQPTConfig,
    ptm_frobenius_error,
    simulate_qpt_estimate,
    single_qubit_process,
)
from oqs_control.hardware.projected_qpt import (
    choi_physicality,
    choi_to_ptm,
    partial_trace_output,
    project_cptp_dykstra,
    project_positive_semidefinite,
    project_trace_preserving,
    projected_least_squares_qpt,
    ptm_to_choi,
)


def test_ptm_choi_round_trip_for_physical_process() -> None:
    _, actual = single_qubit_process()
    choi = ptm_to_choi(actual)
    recovered = choi_to_ptm(choi)

    assert np.allclose(recovered, actual, atol=1e-12)


def test_physical_process_choi_is_positive_and_trace_preserving() -> None:
    _, actual = single_qubit_process()
    physicality = choi_physicality(ptm_to_choi(actual))

    assert physicality.min_eigenvalue >= -1e-12
    assert physicality.trace_preserving_residual < 1e-12
    assert np.isclose(physicality.trace_value, 2.0)


def test_trace_preserving_projection_enforces_partial_trace() -> None:
    matrix = np.diag([1.2, 0.4, 0.3, 0.1]).astype(complex)
    projected = project_trace_preserving(matrix)

    assert np.allclose(partial_trace_output(projected), np.eye(2), atol=1e-12)


def test_positive_projection_removes_negative_eigenvalues() -> None:
    matrix = np.diag([1.0, 0.8, 0.2, -0.1]).astype(complex)
    projected = project_positive_semidefinite(matrix)

    assert np.min(np.linalg.eigvalsh(projected).real) >= -1e-12


def test_cptp_projection_is_physical() -> None:
    matrix = np.diag([1.2, 0.8, 0.2, -0.1]).astype(complex)
    projected = project_cptp_dykstra(matrix, iterations=80)
    physicality = choi_physicality(projected)

    assert physicality.min_eigenvalue >= -1e-7
    assert physicality.trace_preserving_residual < 1e-7


def test_projected_ls_qpt_outputs_physical_channel() -> None:
    _, actual = single_qubit_process()
    config = MultipassQPTConfig(
        shots=128,
        readout_scale=1.0,
        readout_bias_x=0.0,
        readout_bias_y=0.0,
        readout_bias_z=0.0,
        prep_shrink=1.0,
        prep_bias_x=0.0,
        prep_bias_y=0.0,
        prep_bias_z=0.0,
    )
    rng = np.random.default_rng(321)
    raw = simulate_qpt_estimate(actual, 1, config, rng)
    projected = projected_least_squares_qpt(raw, iterations=80)

    assert projected.cptp_physicality.min_eigenvalue >= -1e-7
    assert projected.cptp_physicality.trace_preserving_residual < 1e-7
    assert ptm_frobenius_error(projected.cptp_ptm, actual) < 2.0
