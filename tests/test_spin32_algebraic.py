from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from oqs_control.open_systems.lindblad import density_matrix_to_vector, vector_to_density_matrix
from oqs_control.platforms.na23_nmr import NMRConfig
from oqs_control.platforms.na23_nmr.algebraic_spin32 import (
    coherence_order_weights,
    detector_row,
    deviation_density,
    signal_energy,
    simulate_algebraic_one_pulse_fid,
    trace_row,
    unitary_superoperator,
)
from oqs_control.platforms.na23_nmr.simulation import simulate_fid


def test_unitary_superoperator_matches_density_matrix_propagation() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    unitary = expm(-1j * config.h_free * config.dwell_time)
    rho = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T

    propagated_vec = unitary_superoperator(unitary) @ density_matrix_to_vector(rho)
    propagated_rho = vector_to_density_matrix(propagated_vec, config.dim)
    expected = unitary @ rho @ unitary.conj().T

    assert np.allclose(propagated_rho, expected, atol=1e-12)


def test_detector_row_matches_trace_observable() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    rho = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T

    vector_signal = detector_row(config.detector) @ density_matrix_to_vector(rho)
    trace_signal = np.trace(rho @ config.detector)

    assert np.allclose(vector_signal, trace_signal, atol=1e-12)


def test_reference_fid_matches_algebraic_superoperator_without_decay() -> None:
    no_decay = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
        ],
        dtype=float,
    )
    config = NMRConfig(n_acq=96, n_zf=96, decay_params=no_decay)

    reference_fid = simulate_fid(config, n_points=96)
    algebraic = simulate_algebraic_one_pulse_fid(config, n_points=96)

    assert np.max(np.abs(reference_fid - algebraic.fid)) < 1e-12


def test_trace_row_is_left_invariant_for_unitary_superoperator() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    unitary = expm(-1j * config.h_free * config.dwell_time)
    superop = unitary_superoperator(unitary)

    assert np.allclose(trace_row(config.dim) @ superop, trace_row(config.dim), atol=1e-12)


def test_coherence_order_weights_are_normalized_for_deviation_state() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    weights = coherence_order_weights(deviation_density(config), config.m_vals)

    assert np.isclose(sum(weights.values()), 1.0)
    assert weights[0] > 0.999


def test_b1_scale_changes_one_pulse_signal_energy() -> None:
    config = NMRConfig(n_acq=96, n_zf=96)
    weak = simulate_algebraic_one_pulse_fid(config, n_points=96, b1_scale=0.4)
    nominal = simulate_algebraic_one_pulse_fid(config, n_points=96, b1_scale=1.0)

    assert signal_energy(nominal.fid) > signal_energy(weak.fid)
