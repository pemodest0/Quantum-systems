from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr import NMRConfig
from oqs_control.platforms.na23_nmr.quadrupolar_qip import (
    decompose_in_product_operator_basis,
    deviation_fidelity,
    projector,
    pseudo_pure_state,
    quadrupolar_traceless_operator,
    reconstruct_from_product_coefficients,
    run_grover_search,
)


def test_pseudo_pure_state_is_valid_density_matrix() -> None:
    rho = pseudo_pure_state(2, epsilon=0.08)

    assert np.allclose(rho, rho.conj().T)
    assert np.isclose(np.trace(rho), 1.0)
    assert np.min(np.linalg.eigvalsh(rho).real) >= -1e-12


def test_two_qubit_grover_search_marks_each_basis_state() -> None:
    for marked_index in range(4):
        result = run_grover_search(marked_index, epsilon=1.0)

        assert np.argmax(result.final_populations) == marked_index
        assert result.marked_population > 1.0 - 1e-12
        assert result.deviation_fidelity > 1.0 - 1e-12


def test_pseudo_pure_grover_preserves_deviation_direction() -> None:
    result = run_grover_search(3, epsilon=0.03)
    target = pseudo_pure_state(3, epsilon=0.9)

    assert np.isclose(result.marked_population, 0.25 + 0.75 * 0.03)
    assert deviation_fidelity(result.final_state, target) > 1.0 - 1e-12


def test_spin32_iz_decomposes_as_logical_zi_plus_half_iz() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    coeffs = decompose_in_product_operator_basis(config.i_z)
    reconstructed = reconstruct_from_product_coefficients(coeffs)

    assert np.allclose(reconstructed, config.i_z)
    assert np.isclose(coeffs["ZI"], 1.0)
    assert np.isclose(coeffs["IZ"], 0.5)
    for label, value in coeffs.items():
        if label not in {"ZI", "IZ"}:
            assert abs(value) < 1e-12


def test_first_order_quadrupolar_term_is_logical_zz() -> None:
    config = NMRConfig(n_acq=32, n_zf=32)
    q_op = quadrupolar_traceless_operator(config.i_spin, config.i_z2)
    coeffs = decompose_in_product_operator_basis(q_op)
    reconstructed = reconstruct_from_product_coefficients(coeffs)

    assert np.allclose(reconstructed, q_op)
    assert np.isclose(coeffs["ZZ"], 3.0)
    for label, value in coeffs.items():
        if label != "ZZ":
            assert abs(value) < 1e-12


def test_projector_decomposition_round_trip() -> None:
    rho = projector(1)
    coeffs = decompose_in_product_operator_basis(rho)

    assert np.allclose(reconstruct_from_product_coefficients(coeffs), rho)
