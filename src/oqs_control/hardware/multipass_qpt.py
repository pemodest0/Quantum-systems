from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm, logm


@dataclass(frozen=True)
class MultipassQPTConfig:
    shots: int = 512
    readout_scale: float = 0.93
    readout_bias_x: float = 0.025
    readout_bias_y: float = -0.018
    readout_bias_z: float = 0.035
    prep_shrink: float = 0.97
    prep_bias_x: float = 0.015
    prep_bias_y: float = -0.012
    prep_bias_z: float = 0.02


@dataclass(frozen=True)
class QPTEstimate:
    passes: int
    measured_ptm_power: np.ndarray
    estimated_single_ptm: np.ndarray
    raw_single_pass_ptm: np.ndarray | None = None


@dataclass(frozen=True)
class QPTMonteCarloResult:
    passes: tuple[int, ...]
    single_errors: np.ndarray
    multipass_errors: dict[int, np.ndarray]
    improvement_factors: dict[int, float]


def pauli_matrices() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    identity = np.eye(2, dtype=complex)
    sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
    return identity, sigma_x, sigma_y, sigma_z


def rotation_unitary(axis: str, angle_rad: float) -> np.ndarray:
    _, sigma_x, sigma_y, sigma_z = pauli_matrices()
    axes = {
        "x": sigma_x,
        "y": sigma_y,
        "z": sigma_z,
    }
    if axis.lower() not in axes:
        raise ValueError("axis must be x, y, or z")
    sigma = axes[axis.lower()]
    return expm(-0.5j * float(angle_rad) * sigma)


def unitary_to_ptm(unitary: np.ndarray) -> np.ndarray:
    basis = pauli_matrices()
    u = np.asarray(unitary, dtype=complex)
    ptm = np.zeros((4, 4), dtype=float)
    for row, p_row in enumerate(basis):
        for col, p_col in enumerate(basis):
            evolved = u @ p_col @ u.conj().T
            ptm[row, col] = float(np.real(np.trace(p_row @ evolved)) / 2.0)
    return ptm


def depolarizing_ptm(probability: float) -> np.ndarray:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    shrink = 1.0 - float(probability)
    return np.diag([1.0, shrink, shrink, shrink])


def dephasing_z_ptm(probability: float) -> np.ndarray:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    shrink = 1.0 - 2.0 * float(probability)
    return np.diag([1.0, shrink, shrink, 1.0])


def single_qubit_process(
    target_angle_rad: float = np.pi / 2.0,
    coherent_overrotation_rad: float = 0.035,
    depolarizing_probability: float = 0.006,
    dephasing_probability: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return target and actual PTMs for a noisy sqrt-X-like gate."""

    target = unitary_to_ptm(rotation_unitary("x", target_angle_rad))
    actual_unitary = unitary_to_ptm(
        rotation_unitary("x", target_angle_rad + coherent_overrotation_rad)
    )
    noise = depolarizing_ptm(depolarizing_probability) @ dephasing_z_ptm(dephasing_probability)
    actual = noise @ actual_unitary
    return target, actual


def ideal_input_stokes() -> np.ndarray:
    """Return columns [1, x, y, z] for four single-qubit input states."""

    bloch = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=float,
    )
    return np.vstack([np.ones(4), bloch.T])


def _prepared_stokes(config: MultipassQPTConfig) -> np.ndarray:
    ideal = ideal_input_stokes()
    bias = np.array([config.prep_bias_x, config.prep_bias_y, config.prep_bias_z], dtype=float)
    prepared = np.array(ideal, copy=True)
    for col in range(prepared.shape[1]):
        vec = config.prep_shrink * prepared[1:, col] + bias
        norm = np.linalg.norm(vec)
        if norm > 1.0:
            vec = vec / norm
        prepared[1:, col] = vec
    return prepared


def _measure_bloch(
    bloch: np.ndarray,
    config: MultipassQPTConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    readout_bias = np.array(
        [config.readout_bias_x, config.readout_bias_y, config.readout_bias_z],
        dtype=float,
    )
    raw = config.readout_scale * np.asarray(bloch, dtype=float) + readout_bias
    clipped_true = np.clip(raw, -1.0, 1.0)
    shot_std = np.sqrt(np.maximum(1.0 - clipped_true**2, 0.0) / max(config.shots, 1))
    noisy = clipped_true + rng.normal(scale=shot_std)
    return np.clip(noisy, -1.0, 1.0)


def apply_ptm(ptm: np.ndarray, stokes: np.ndarray) -> np.ndarray:
    return np.asarray(ptm, dtype=float) @ np.asarray(stokes, dtype=float)


def simulate_qpt_estimate(
    process_ptm: np.ndarray,
    passes: int,
    config: MultipassQPTConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Estimate the PTM of process^passes by standard single-qubit QPT."""

    if passes <= 0:
        raise ValueError("passes must be positive")
    process_power = np.linalg.matrix_power(np.asarray(process_ptm, dtype=float), int(passes))
    prepared_inputs = _prepared_stokes(config)
    ideal_inputs = ideal_input_stokes()
    measured_outputs = np.zeros((4, 4), dtype=float)

    for col in range(ideal_inputs.shape[1]):
        output = process_power @ prepared_inputs[:, col]
        measured_bloch = _measure_bloch(output[1:], config, rng)
        measured_outputs[:, col] = np.concatenate([[1.0], measured_bloch])

    estimated = measured_outputs @ np.linalg.inv(ideal_inputs)
    estimated[0, :] = np.array([1.0, 0.0, 0.0, 0.0])
    return estimated


def matrix_root_near_identity(matrix: np.ndarray, passes: int) -> np.ndarray:
    if passes <= 0:
        raise ValueError("passes must be positive")
    root = expm(logm(np.asarray(matrix, dtype=float)) / float(passes))
    return np.real_if_close(root, tol=1_000).real


def estimate_single_process_from_multipass(
    measured_process_power: np.ndarray,
    target_ptm: np.ndarray,
    passes: int,
) -> np.ndarray:
    """Estimate a single-process PTM from a measured multipass PTM.

    The root is taken in the target error frame to avoid branch ambiguity for
    non-identity gates such as sqrt-X.
    """

    if passes <= 0:
        raise ValueError("passes must be positive")
    target_power = np.linalg.matrix_power(np.asarray(target_ptm, dtype=float), int(passes))
    error_power = np.asarray(measured_process_power, dtype=float) @ np.linalg.inv(target_power)
    error_root = matrix_root_near_identity(error_power, passes)
    estimated = error_root @ np.asarray(target_ptm, dtype=float)
    estimated[0, :] = np.array([1.0, 0.0, 0.0, 0.0])
    return estimated


def ptm_frobenius_error(estimated: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(estimated, dtype=float) - np.asarray(reference, dtype=float)))


def average_output_bloch_fidelity(estimated: np.ndarray, reference: np.ndarray) -> float:
    inputs = ideal_input_stokes()
    fidelities: list[float] = []
    for col in range(inputs.shape[1]):
        ref = (np.asarray(reference, dtype=float) @ inputs[:, col])[1:]
        est = (np.asarray(estimated, dtype=float) @ inputs[:, col])[1:]
        value = 0.5 * (1.0 + np.dot(ref, est) + np.sqrt(max(0.0, 1.0 - np.dot(ref, ref))) * np.sqrt(max(0.0, 1.0 - np.dot(est, est))))
        fidelities.append(float(np.clip(value, 0.0, 1.0)))
    return float(np.mean(fidelities))


def run_multipass_monte_carlo(
    passes: tuple[int, ...],
    shots: int,
    seeds: tuple[int, ...],
    config: MultipassQPTConfig | None = None,
) -> tuple[np.ndarray, np.ndarray, QPTMonteCarloResult]:
    base_config = config or MultipassQPTConfig(shots=shots)
    active_config = MultipassQPTConfig(
        shots=shots,
        readout_scale=base_config.readout_scale,
        readout_bias_x=base_config.readout_bias_x,
        readout_bias_y=base_config.readout_bias_y,
        readout_bias_z=base_config.readout_bias_z,
        prep_shrink=base_config.prep_shrink,
        prep_bias_x=base_config.prep_bias_x,
        prep_bias_y=base_config.prep_bias_y,
        prep_bias_z=base_config.prep_bias_z,
    )
    target, actual = single_qubit_process()
    single_errors: list[float] = []
    multipass_errors: dict[int, list[float]] = {passes_n: [] for passes_n in passes}

    for seed in seeds:
        rng = np.random.default_rng(seed)
        single_est = simulate_qpt_estimate(actual, 1, active_config, rng)
        single_errors.append(ptm_frobenius_error(single_est, actual))
        for passes_n in passes:
            measured_power = simulate_qpt_estimate(actual, passes_n, active_config, rng)
            estimated_single = estimate_single_process_from_multipass(
                measured_power,
                target,
                passes_n,
            )
            multipass_errors[passes_n].append(ptm_frobenius_error(estimated_single, actual))

    single_array = np.asarray(single_errors, dtype=float)
    multi_arrays = {passes_n: np.asarray(values, dtype=float) for passes_n, values in multipass_errors.items()}
    single_mean = float(np.mean(single_array))
    improvement = {
        passes_n: single_mean / max(float(np.mean(values)), 1e-15)
        for passes_n, values in multi_arrays.items()
    }
    return target, actual, QPTMonteCarloResult(
        passes=passes,
        single_errors=single_array,
        multipass_errors=multi_arrays,
        improvement_factors=improvement,
    )
