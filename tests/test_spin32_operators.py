from __future__ import annotations

import numpy as np

from oqs_control.platforms.na23_nmr.operators import spin_operators


def test_spin32_commutation_relations() -> None:
    ops = spin_operators(1.5)

    assert np.allclose(ops.i_x @ ops.i_y - ops.i_y @ ops.i_x, 1j * ops.i_z, atol=1e-12)
    assert np.allclose(ops.i_y @ ops.i_z - ops.i_z @ ops.i_y, 1j * ops.i_x, atol=1e-12)
    assert np.allclose(ops.i_z @ ops.i_x - ops.i_x @ ops.i_z, 1j * ops.i_y, atol=1e-12)


def test_spin32_hermiticity_traces_and_ladder_adjoint() -> None:
    ops = spin_operators(1.5)

    assert np.allclose(ops.i_x, ops.i_x.conj().T, atol=1e-12)
    assert np.allclose(ops.i_y, ops.i_y.conj().T, atol=1e-12)
    assert np.allclose(ops.i_z, ops.i_z.conj().T, atol=1e-12)
    assert np.allclose(ops.i_plus, ops.i_minus.conj().T, atol=1e-12)
    assert abs(np.trace(ops.i_x)) < 1e-12
    assert abs(np.trace(ops.i_y)) < 1e-12
    assert abs(np.trace(ops.i_z)) < 1e-12


def test_spin32_iz_spectrum_and_casimir() -> None:
    ops = spin_operators(1.5)
    identity = np.eye(4, dtype=complex)
    casimir = ops.i_x @ ops.i_x + ops.i_y @ ops.i_y + ops.i_z @ ops.i_z

    assert np.allclose(sorted(np.linalg.eigvalsh(ops.i_z).real), [-1.5, -0.5, 0.5, 1.5])
    assert np.allclose(casimir, 1.5 * 2.5 * identity, atol=1e-12)
