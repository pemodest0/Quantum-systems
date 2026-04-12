from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from oqs_control.open_systems.lindblad import (
    density_matrix_to_vector,
    liouvillian,
    vector_to_density_matrix,
)
from oqs_control.platforms.na23_nmr import NMRConfig, NMRDissipationRates, nmr_liouvillian
from oqs_control.platforms.na23_nmr.liouvillian import simulate_open_fid


def test_liouvillian_trace_preservation_as_left_null_vector() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    l_op = nmr_liouvillian(config, NMRDissipationRates(gamma_phi=120.0, gamma_relax=25.0))
    trace_row = np.eye(config.dim, dtype=complex).reshape(-1, order="F").conj()

    assert np.allclose(trace_row @ l_op, 0.0, atol=1e-10)


def test_zero_dissipation_liouvillian_matches_unitary_propagation() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    rho0 = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T
    times, _, states = simulate_open_fid(
        config,
        rates=NMRDissipationRates(gamma_phi=0.0, gamma_relax=0.0),
        rho0=rho0,
        n_points=8,
        include_dead_time=False,
    )

    for idx, time_s in enumerate(times):
        unitary = expm(-1j * config.h_free * time_s)
        expected = unitary @ rho0 @ unitary.conj().T
        assert np.allclose(states[idx], expected, atol=1e-10)


def test_generic_liouvillian_zero_jump_matches_commutator_form() -> None:
    hamiltonian = np.array([[0.5, 0.1], [0.1, -0.5]], dtype=complex)
    rho = np.array([[0.7, 0.2j], [-0.2j, 0.3]], dtype=complex)
    l_op = liouvillian(hamiltonian, [])
    rhs = vector_to_density_matrix(l_op @ density_matrix_to_vector(rho), 2)
    expected = -1j * (hamiltonian @ rho - rho @ hamiltonian)

    assert np.allclose(rhs, expected, atol=1e-12)
