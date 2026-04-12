from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
from scipy.optimize import minimize_scalar


ControlSequence = tuple[str, ...]


@dataclass(frozen=True)
class CorrelatedDephasingConfig:
    phase_rad: float = 0.72
    p_stay: float = 0.92
    shots: int = 4096


@dataclass(frozen=True)
class ProcessTensorDataset:
    sequences: tuple[ControlSequence, ...]
    probabilities: np.ndarray
    counts: np.ndarray
    shots: int


@dataclass(frozen=True)
class MarkovianChannelFit:
    lambda_xy: float
    train_rmse: float
    success: bool


def rotation_matrix(axis: str, angle_rad: float) -> np.ndarray:
    c = np.cos(float(angle_rad))
    s = np.sin(float(angle_rad))
    axis_l = axis.lower()
    if axis_l == "x":
        return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=float)
    if axis_l == "y":
        return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=float)
    if axis_l == "z":
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)
    raise ValueError("axis must be x, y, or z")


def control_library() -> dict[str, np.ndarray]:
    return {
        "i": np.eye(3, dtype=float),
        "x": rotation_matrix("x", np.pi),
        "y": rotation_matrix("y", np.pi),
        "x2": rotation_matrix("x", np.pi / 2.0),
        "y2": rotation_matrix("y", np.pi / 2.0),
    }


def make_control_sequences(length: int, controls: tuple[str, ...] = ("i", "x", "y", "x2", "y2")) -> tuple[ControlSequence, ...]:
    return tuple(tuple(sequence) for sequence in product(controls, repeat=int(length)))


def _transition_probability(next_hidden: int, current_hidden: int, p_stay: float) -> float:
    return float(p_stay) if int(next_hidden) == int(current_hidden) else 1.0 - float(p_stay)


def final_bloch_correlated_dephasing(
    sequence: ControlSequence,
    config: CorrelatedDephasingConfig,
    initial_bloch: np.ndarray | None = None,
) -> np.ndarray:
    controls = control_library()
    initial = np.array([1.0, 0.0, 0.0], dtype=float) if initial_bloch is None else np.asarray(initial_bloch, dtype=float)
    hidden_values = (-1, 1)
    weighted_state = np.zeros(3, dtype=float)

    for hidden_path in product(hidden_values, repeat=len(sequence) + 1):
        path_probability = 0.5
        for idx in range(1, len(hidden_path)):
            path_probability *= _transition_probability(hidden_path[idx], hidden_path[idx - 1], config.p_stay)
        state = np.array(initial, copy=True)
        for interval_idx, control_name in enumerate(sequence):
            state = rotation_matrix("z", hidden_path[interval_idx] * config.phase_rad) @ state
            state = controls[control_name] @ state
        state = rotation_matrix("z", hidden_path[-1] * config.phase_rad) @ state
        weighted_state += path_probability * state
    return weighted_state


def x_measurement_probability(bloch: np.ndarray) -> float:
    return float(np.clip(0.5 * (1.0 + np.asarray(bloch, dtype=float)[0]), 1e-9, 1.0 - 1e-9))


def sequence_probability(sequence: ControlSequence, config: CorrelatedDephasingConfig) -> float:
    return x_measurement_probability(final_bloch_correlated_dephasing(sequence, config))


def simulate_process_tensor_dataset(
    sequences: tuple[ControlSequence, ...],
    config: CorrelatedDephasingConfig,
    seed: int,
) -> ProcessTensorDataset:
    rng = np.random.default_rng(seed)
    probabilities = np.array([sequence_probability(sequence, config) for sequence in sequences], dtype=float)
    counts = rng.binomial(config.shots, probabilities)
    observed = counts.astype(float) / float(config.shots)
    return ProcessTensorDataset(
        sequences=sequences,
        probabilities=observed,
        counts=counts,
        shots=config.shots,
    )


def markovian_prediction(sequence: ControlSequence, lambda_xy: float) -> float:
    controls = control_library()
    state = np.array([1.0, 0.0, 0.0], dtype=float)
    channel = np.diag([float(lambda_xy), float(lambda_xy), 1.0])
    for control_name in sequence:
        state = channel @ state
        state = controls[control_name] @ state
    state = channel @ state
    return x_measurement_probability(state)


def fit_markovian_channel(dataset: ProcessTensorDataset) -> MarkovianChannelFit:
    def objective(lambda_xy: float) -> float:
        predicted = np.array([markovian_prediction(sequence, lambda_xy) for sequence in dataset.sequences], dtype=float)
        return float(np.mean((predicted - dataset.probabilities) ** 2))

    result = minimize_scalar(objective, bounds=(-1.0, 1.0), method="bounded", options={"xatol": 1e-10})
    best = float(result.x)
    return MarkovianChannelFit(
        lambda_xy=best,
        train_rmse=float(np.sqrt(objective(best))),
        success=bool(result.success),
    )


def prediction_rmse_markovian(dataset: ProcessTensorDataset, fit: MarkovianChannelFit) -> float:
    predicted = np.array([markovian_prediction(sequence, fit.lambda_xy) for sequence in dataset.sequences], dtype=float)
    return float(np.sqrt(np.mean((predicted - dataset.probabilities) ** 2)))


def prediction_rmse_process_tensor(
    predicted_dataset: ProcessTensorDataset,
    observed_dataset: ProcessTensorDataset,
) -> float:
    lookup = {
        sequence: probability
        for sequence, probability in zip(predicted_dataset.sequences, predicted_dataset.probabilities)
    }
    predicted = np.array([lookup[sequence] for sequence in observed_dataset.sequences], dtype=float)
    return float(np.sqrt(np.mean((predicted - observed_dataset.probabilities) ** 2)))


def best_sequence_from_dataset(dataset: ProcessTensorDataset) -> tuple[ControlSequence, float]:
    idx = int(np.argmax(dataset.probabilities))
    return dataset.sequences[idx], float(dataset.probabilities[idx])


def best_sequence_markovian(sequences: tuple[ControlSequence, ...], fit: MarkovianChannelFit) -> tuple[ControlSequence, float]:
    probabilities = np.array([markovian_prediction(sequence, fit.lambda_xy) for sequence in sequences], dtype=float)
    idx = int(np.argmax(probabilities))
    return sequences[idx], float(probabilities[idx])


def process_tensor_memory_witness(dataset: ProcessTensorDataset) -> dict[str, float]:
    lookup = {
        sequence: probability
        for sequence, probability in zip(dataset.sequences, dataset.probabilities)
    }
    echo_like = lookup.get(("x",), np.nan)
    free_like = lookup.get(("i",), np.nan)
    xx_echo = lookup.get(("x", "x"), np.nan)
    ii_free = lookup.get(("i", "i"), np.nan)
    return {
        "single_echo_minus_free": float(echo_like - free_like),
        "two_pulse_xx_minus_ii": float(xx_echo - ii_free),
        "probability_range": float(np.max(dataset.probabilities) - np.min(dataset.probabilities)),
    }


def sequence_to_label(sequence: ControlSequence) -> str:
    return "-".join(sequence) if sequence else "empty"
