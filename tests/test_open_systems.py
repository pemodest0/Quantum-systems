from __future__ import annotations

from pathlib import Path

import numpy as np

from oqs_control import (
    ControlSegment,
    gate_fidelity,
    mesolve,
    piecewise_constant_propagator,
    purity,
    von_neumann_entropy,
)
from oqs_control.platforms.na23_nmr.analysis import summarize_reference
from oqs_control.workflows import run_open_qubit_demo


def pauli_x() -> np.ndarray:
    return np.array([[0, 1], [1, 0]], dtype=complex)


def pauli_z() -> np.ndarray:
    return np.array([[1, 0], [0, -1]], dtype=complex)


def sigma_minus() -> np.ndarray:
    return np.array([[0, 0], [1, 0]], dtype=complex)


def test_mesolve_preserves_trace_and_hermiticity() -> None:
    hamiltonian = 0.5 * pauli_z() + 0.25 * pauli_x()
    rho0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    times = np.linspace(0.0, 2.0, 60)
    result = mesolve(
        hamiltonian=hamiltonian,
        rho0=rho0,
        times=times,
        jump_operators=[np.sqrt(0.2) * sigma_minus()],
    )

    assert result.states.shape == (times.size, 2, 2)
    traces = np.trace(result.states, axis1=1, axis2=2)
    assert np.allclose(traces, 1.0, atol=1e-9)
    assert np.allclose(result.states, np.conjugate(np.swapaxes(result.states, 1, 2)), atol=1e-9)


def test_purity_and_entropy_for_pure_state() -> None:
    rho = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    assert np.isclose(purity(rho), 1.0)
    assert np.isclose(von_neumann_entropy(rho), 0.0)


def test_piecewise_constant_propagator_and_fidelity() -> None:
    sx = pauli_x()
    target = np.array(
        [
            [0.0, -1j],
            [-1j, 0.0],
        ],
        dtype=complex,
    )
    unitary = piecewise_constant_propagator(
        [
            ControlSegment(duration=1.0, hamiltonian=0.5 * np.pi * sx)
        ]
    )

    assert np.allclose(unitary @ unitary.conj().T, np.eye(2), atol=1e-9)
    assert np.isclose(gate_fidelity(unitary, unitary), 1.0)
    assert gate_fidelity(unitary, target) > 0.999999


def test_open_qubit_demo_returns_consistent_shapes() -> None:
    result = run_open_qubit_demo(num_points=80)
    assert result.states.shape == (80, 2, 2)
    assert result.purity.shape == (80,)
    assert result.entropy.shape == (80,)
    assert result.entropy_production.shape == (80,)
    assert result.free_energy_like.shape == (80,)


def test_reference_dataset_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    summary = summarize_reference(root / "data" / "reference" / "Referential2.tnt")

    assert summary["magic_ascii"].startswith("TNT")
    assert summary["npoints1d"] == 4096
    assert summary["scans1d"] == 8
    assert len(summary["dominant_peaks"]) >= 3
