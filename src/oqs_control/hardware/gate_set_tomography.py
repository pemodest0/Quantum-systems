from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
from scipy.optimize import least_squares

from .multipass_qpt import rotation_unitary, unitary_to_ptm


GateName = str
GateSequence = tuple[GateName, ...]


@dataclass(frozen=True)
class GateSet:
    prep: np.ndarray
    effect: np.ndarray
    gates: dict[str, np.ndarray]


@dataclass(frozen=True)
class GSTDataset:
    sequences: tuple[GateSequence, ...]
    probabilities: np.ndarray
    counts: np.ndarray
    shots: int


@dataclass(frozen=True)
class GSTFitResult:
    gate_set: GateSet
    residual_norm: float
    rmse: float
    iterations: int
    success: bool
    message: str


def ideal_bloch_gate_set() -> GateSet:
    return GateSet(
        prep=np.array([0.0, 0.0, 1.0], dtype=float),
        effect=np.array([0.5, 0.0, 0.0, 0.5], dtype=float),
        gates={
            "x": unitary_to_ptm(rotation_unitary("x", np.pi / 2.0))[1:, 1:],
            "y": unitary_to_ptm(rotation_unitary("y", np.pi / 2.0))[1:, 1:],
        },
    )


def noisy_bloch_gate_set(
    x_overrotation_rad: float = 0.045,
    y_overrotation_rad: float = -0.035,
    depolarizing_shrink: float = 0.992,
    prep: tuple[float, float, float] = (0.025, -0.018, 0.965),
    effect: tuple[float, float, float, float] = (0.515, 0.018, -0.012, 0.455),
) -> GateSet:
    gx = unitary_to_ptm(rotation_unitary("x", np.pi / 2.0 + x_overrotation_rad))[1:, 1:]
    gy = unitary_to_ptm(rotation_unitary("y", np.pi / 2.0 + y_overrotation_rad))[1:, 1:]
    return GateSet(
        prep=np.array(prep, dtype=float),
        effect=np.array(effect, dtype=float),
        gates={
            "x": float(depolarizing_shrink) * gx,
            "y": float(depolarizing_shrink) * gy,
        },
    )


def apply_sequence(gate_set: GateSet, sequence: GateSequence) -> np.ndarray:
    state = np.asarray(gate_set.prep, dtype=float)
    for gate_name in sequence:
        state = np.asarray(gate_set.gates[gate_name], dtype=float) @ state
    return state


def sequence_probability(gate_set: GateSet, sequence: GateSequence) -> float:
    state = apply_sequence(gate_set, sequence)
    effect = np.asarray(gate_set.effect, dtype=float)
    probability = float(effect[0] + np.dot(effect[1:], state))
    return float(np.clip(probability, 1e-9, 1.0 - 1e-9))


def sequence_probabilities(gate_set: GateSet, sequences: tuple[GateSequence, ...]) -> np.ndarray:
    return np.array([sequence_probability(gate_set, sequence) for sequence in sequences], dtype=float)


def make_gst_sequences(
    max_repeat: int = 16,
    include_fiducials: bool = True,
) -> tuple[GateSequence, ...]:
    germs: tuple[GateSequence, ...] = (
        ("x",),
        ("y",),
        ("x", "y"),
        ("x", "x", "y"),
        ("x", "y", "y"),
    )
    repeats = [1, 2, 4, 8, 16]
    repeats = [value for value in repeats if value <= int(max_repeat)]
    fiducials: tuple[GateSequence, ...] = ((),)
    if include_fiducials:
        fiducials = ((), ("x",), ("y",), ("x", "x"), ("y", "y"))

    sequences: set[GateSequence] = {()}
    for length in range(1, 4):
        for word in product(("x", "y"), repeat=length):
            sequences.add(tuple(word))
    for germ in germs:
        for repeat in repeats:
            body = germ * repeat
            for left in fiducials:
                for right in fiducials:
                    sequences.add(tuple(left + body + right))
    return tuple(sorted(sequences, key=lambda item: (len(item), item)))


def split_train_test_sequences(
    sequences: tuple[GateSequence, ...],
    heldout_min_length: int = 20,
) -> tuple[tuple[GateSequence, ...], tuple[GateSequence, ...]]:
    train = tuple(sequence for sequence in sequences if len(sequence) < int(heldout_min_length))
    test = tuple(sequence for sequence in sequences if len(sequence) >= int(heldout_min_length))
    return train, test


def simulate_dataset(
    gate_set: GateSet,
    sequences: tuple[GateSequence, ...],
    shots: int,
    seed: int,
) -> GSTDataset:
    rng = np.random.default_rng(seed)
    probabilities = sequence_probabilities(gate_set, sequences)
    counts = rng.binomial(int(shots), probabilities)
    observed = counts.astype(float) / float(shots)
    return GSTDataset(
        sequences=sequences,
        probabilities=observed,
        counts=counts,
        shots=int(shots),
    )


def _pack_gate_only(gates: dict[str, np.ndarray]) -> np.ndarray:
    return np.concatenate([gates["x"].reshape(-1), gates["y"].reshape(-1)])


def _unpack_gate_only(params: np.ndarray, fixed: GateSet) -> GateSet:
    values = np.asarray(params, dtype=float)
    gx = values[:9].reshape(3, 3)
    gy = values[9:18].reshape(3, 3)
    return GateSet(
        prep=np.array(fixed.prep, copy=True),
        effect=np.array(fixed.effect, copy=True),
        gates={"x": gx, "y": gy},
    )


def _pack_full(gate_set: GateSet) -> np.ndarray:
    return np.concatenate(
        [
            np.asarray(gate_set.prep, dtype=float),
            np.asarray(gate_set.effect, dtype=float),
            gate_set.gates["x"].reshape(-1),
            gate_set.gates["y"].reshape(-1),
        ]
    )


def _unpack_full(params: np.ndarray) -> GateSet:
    values = np.asarray(params, dtype=float)
    prep = values[0:3]
    effect = values[3:7]
    gx = values[7:16].reshape(3, 3)
    gy = values[16:25].reshape(3, 3)
    return GateSet(prep=prep, effect=effect, gates={"x": gx, "y": gy})


def residuals_for_dataset(gate_set: GateSet, dataset: GSTDataset, weighted: bool = True) -> np.ndarray:
    predicted = sequence_probabilities(gate_set, dataset.sequences)
    residual = predicted - np.asarray(dataset.probabilities, dtype=float)
    if not weighted:
        return residual
    variance = np.maximum(predicted * (1.0 - predicted), 1e-6) / float(dataset.shots)
    return residual / np.sqrt(variance)


def fit_gate_only_model(
    dataset: GSTDataset,
    initial: GateSet | None = None,
    max_iter: int = 400,
) -> GSTFitResult:
    fixed = initial or ideal_bloch_gate_set()
    x0 = _pack_gate_only(fixed.gates)

    def objective(params: np.ndarray) -> np.ndarray:
        return residuals_for_dataset(_unpack_gate_only(params, fixed), dataset, weighted=True)

    result = least_squares(
        objective,
        x0,
        bounds=(-1.3, 1.3),
        max_nfev=int(max_iter),
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )
    fitted = _unpack_gate_only(result.x, fixed)
    residual = residuals_for_dataset(fitted, dataset, weighted=False)
    return GSTFitResult(
        gate_set=fitted,
        residual_norm=float(np.linalg.norm(residual)),
        rmse=float(np.sqrt(np.mean(residual**2))),
        iterations=int(result.nfev),
        success=bool(result.success),
        message=str(result.message),
    )


def fit_gate_set_model(
    dataset: GSTDataset,
    initial: GateSet | None = None,
    max_iter: int = 700,
) -> GSTFitResult:
    start = initial or ideal_bloch_gate_set()
    x0 = _pack_full(start)
    lower = np.concatenate(
        [
            -np.ones(3),
            np.array([0.0, -1.0, -1.0, -1.0]),
            -1.3 * np.ones(18),
        ]
    )
    upper = np.concatenate(
        [
            np.ones(3),
            np.array([1.0, 1.0, 1.0, 1.0]),
            1.3 * np.ones(18),
        ]
    )

    def objective(params: np.ndarray) -> np.ndarray:
        return residuals_for_dataset(_unpack_full(params), dataset, weighted=True)

    result = least_squares(
        objective,
        x0,
        bounds=(lower, upper),
        max_nfev=int(max_iter),
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
    )
    fitted = _unpack_full(result.x)
    residual = residuals_for_dataset(fitted, dataset, weighted=False)
    return GSTFitResult(
        gate_set=fitted,
        residual_norm=float(np.linalg.norm(residual)),
        rmse=float(np.sqrt(np.mean(residual**2))),
        iterations=int(result.nfev),
        success=bool(result.success),
        message=str(result.message),
    )


def prediction_rmse(gate_set: GateSet, dataset: GSTDataset) -> float:
    predicted = sequence_probabilities(gate_set, dataset.sequences)
    residual = predicted - np.asarray(dataset.probabilities, dtype=float)
    return float(np.sqrt(np.mean(residual**2)))


def gate_matrix_error(estimated: GateSet, reference: GateSet) -> dict[str, float]:
    return {
        name: float(np.linalg.norm(estimated.gates[name] - reference.gates[name]))
        for name in sorted(reference.gates)
    }


def spam_error(estimated: GateSet, reference: GateSet) -> dict[str, float]:
    return {
        "prep": float(np.linalg.norm(estimated.prep - reference.prep)),
        "effect": float(np.linalg.norm(estimated.effect - reference.effect)),
    }


def sequence_lengths(sequences: tuple[GateSequence, ...]) -> np.ndarray:
    return np.array([len(sequence) for sequence in sequences], dtype=int)


def rmse_by_length(gate_set: GateSet, dataset: GSTDataset) -> list[dict[str, float]]:
    lengths = sequence_lengths(dataset.sequences)
    predicted = sequence_probabilities(gate_set, dataset.sequences)
    residual = predicted - dataset.probabilities
    rows: list[dict[str, float]] = []
    for length in sorted(set(int(value) for value in lengths)):
        mask = lengths == length
        rows.append(
            {
                "length": int(length),
                "count": int(np.count_nonzero(mask)),
                "rmse": float(np.sqrt(np.mean(residual[mask] ** 2))),
            }
        )
    return rows


def sequence_to_label(sequence: GateSequence) -> str:
    return "".join(sequence) if sequence else "empty"
