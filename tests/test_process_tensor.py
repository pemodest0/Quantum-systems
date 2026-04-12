from __future__ import annotations

import numpy as np

from oqs_control.hardware.process_tensor import (
    CorrelatedDephasingConfig,
    best_sequence_from_dataset,
    best_sequence_markovian,
    fit_markovian_channel,
    make_control_sequences,
    markovian_prediction,
    prediction_rmse_markovian,
    prediction_rmse_process_tensor,
    process_tensor_memory_witness,
    rotation_matrix,
    simulate_process_tensor_dataset,
)


def test_rotation_matrix_is_orthogonal() -> None:
    rot = rotation_matrix("z", 0.37)

    assert np.allclose(rot.T @ rot, np.eye(3))
    assert np.isclose(np.linalg.det(rot), 1.0)


def test_correlated_process_dataset_probabilities_are_valid() -> None:
    config = CorrelatedDephasingConfig(phase_rad=0.7, p_stay=0.9, shots=2048)
    sequences = make_control_sequences(2, controls=("i", "x", "y"))
    dataset = simulate_process_tensor_dataset(sequences, config, seed=1)

    assert dataset.probabilities.shape == (len(sequences),)
    assert np.all(dataset.probabilities >= 0.0)
    assert np.all(dataset.probabilities <= 1.0)


def test_markovian_fit_returns_valid_lambda() -> None:
    config = CorrelatedDephasingConfig(phase_rad=0.7, p_stay=0.55, shots=10_000)
    sequences = make_control_sequences(2, controls=("i", "x", "y"))
    dataset = simulate_process_tensor_dataset(sequences, config, seed=2)
    fit = fit_markovian_channel(dataset)

    assert fit.success
    assert -1.0 <= fit.lambda_xy <= 1.0
    assert 0.0 <= markovian_prediction(("i", "x"), fit.lambda_xy) <= 1.0


def test_process_tensor_lookup_beats_markovian_for_memory_data() -> None:
    config = CorrelatedDephasingConfig(phase_rad=0.72, p_stay=0.92, shots=200_000)
    sequences = make_control_sequences(3, controls=("i", "x", "y"))
    train = simulate_process_tensor_dataset(sequences, config, seed=3)
    observed = simulate_process_tensor_dataset(sequences, config, seed=4)
    fit = fit_markovian_channel(train)

    assert prediction_rmse_process_tensor(train, observed) < prediction_rmse_markovian(observed, fit)


def test_memory_witness_detects_control_history_dependence() -> None:
    config = CorrelatedDephasingConfig(phase_rad=0.72, p_stay=0.92, shots=200_000)
    sequences = make_control_sequences(2, controls=("i", "x"))
    dataset = simulate_process_tensor_dataset(sequences, config, seed=5)
    witness = process_tensor_memory_witness(dataset)

    assert witness["two_pulse_xx_minus_ii"] > 0.0
    assert witness["probability_range"] > 0.0


def test_process_tensor_and_markovian_choose_sequences() -> None:
    config = CorrelatedDephasingConfig(phase_rad=0.72, p_stay=0.92, shots=200_000)
    sequences = make_control_sequences(3, controls=("i", "x", "y"))
    dataset = simulate_process_tensor_dataset(sequences, config, seed=6)
    fit = fit_markovian_channel(dataset)

    process_sequence, process_prob = best_sequence_from_dataset(dataset)
    markov_sequence, markov_prob = best_sequence_markovian(sequences, fit)

    assert process_sequence in sequences
    assert markov_sequence in sequences
    assert 0.0 <= process_prob <= 1.0
    assert 0.0 <= markov_prob <= 1.0
