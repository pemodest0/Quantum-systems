from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr import NMRConfig
from oqs_control.platforms.na23_nmr.selective_pulses import (
    evaluate_selective_pulse,
    finite_selective_pulse_unitary,
    ideal_selective_rotation,
    population_transfer_probability,
    selected_transition_frame_hamiltonian,
    transition_axis,
    unitary_operator_fidelity,
)


def test_transition_axis_is_hermitian_and_local_to_pair() -> None:
    axis = transition_axis(4, (1, 2), phase_rad=0.37)

    assert np.allclose(axis, axis.conj().T)
    assert np.count_nonzero(np.abs(axis) > 0.0) == 2
    assert np.allclose(axis[0, :], 0.0)
    assert np.allclose(axis[:, 3], 0.0)


def test_finite_pulse_without_internal_evolution_matches_ideal_rotation() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    pair = config.transition_pairs[1]
    ideal = ideal_selective_rotation(config.dim, pair, np.pi)
    actual = finite_selective_pulse_unitary(
        config,
        pair,
        np.pi,
        duration_s=250e-6,
        include_quadrupolar_evolution=False,
    )

    assert unitary_operator_fidelity(ideal, actual) > 1.0 - 1e-12


def test_selected_transition_frame_zeros_selected_transition_detuning() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    pair = config.transition_pairs[0]
    h_frame = selected_transition_frame_hamiltonian(config, pair)
    row, col = pair
    selected_detuning = float(np.diag(h_frame).real[row] - np.diag(h_frame).real[col])

    assert abs(selected_detuning) < 1e-9


def test_selective_pi_pulse_transfers_population_without_internal_evolution() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    pair = config.transition_pairs[1]
    unitary = finite_selective_pulse_unitary(
        config,
        pair,
        np.pi,
        duration_s=200e-6,
        include_quadrupolar_evolution=False,
    )

    assert population_transfer_probability(unitary, pair[0], pair[1]) > 1.0 - 1e-12
    assert population_transfer_probability(unitary, pair[1], pair[0]) > 1.0 - 1e-12


def test_quadrupolar_evolution_degrades_long_selective_pulse_more_than_short_one() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    short = evaluate_selective_pulse(
        config,
        transition_index=1,
        angle_rad=np.pi,
        duration_s=10e-6,
        include_quadrupolar_evolution=True,
    )
    long = evaluate_selective_pulse(
        config,
        transition_index=1,
        angle_rad=np.pi,
        duration_s=500e-6,
        include_quadrupolar_evolution=True,
    )

    assert short.operator_fidelity > long.operator_fidelity
