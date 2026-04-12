from __future__ import annotations

import numpy as np

from oqs_control.hardware.gate_set_tomography import (
    fit_gate_only_model,
    fit_gate_set_model,
    ideal_bloch_gate_set,
    make_gst_sequences,
    noisy_bloch_gate_set,
    prediction_rmse,
    sequence_probabilities,
    simulate_dataset,
    split_train_test_sequences,
    spam_error,
)


def test_sequence_probabilities_are_valid() -> None:
    gate_set = noisy_bloch_gate_set()
    sequences = make_gst_sequences(max_repeat=2)
    probabilities = sequence_probabilities(gate_set, sequences)

    assert probabilities.shape == (len(sequences),)
    assert np.all(probabilities > 0.0)
    assert np.all(probabilities < 1.0)


def test_train_test_split_has_heldout_long_sequences() -> None:
    sequences = make_gst_sequences(max_repeat=16)
    train, test = split_train_test_sequences(sequences, heldout_min_length=20)

    assert len(train) > 0
    assert len(test) > 0
    assert max(len(sequence) for sequence in train) < 20
    assert min(len(sequence) for sequence in test) >= 20


def test_gate_only_model_can_fit_ideal_noiseless_data() -> None:
    gate_set = ideal_bloch_gate_set()
    sequences = make_gst_sequences(max_repeat=2)
    dataset = simulate_dataset(gate_set, sequences, shots=1_000_000, seed=1)
    dataset = type(dataset)(
        sequences=dataset.sequences,
        probabilities=sequence_probabilities(gate_set, sequences),
        counts=dataset.counts,
        shots=dataset.shots,
    )
    fit = fit_gate_only_model(dataset, max_iter=80)

    assert fit.rmse < 1e-6


def test_gate_set_fit_matches_noiseless_probabilities_in_some_gauge() -> None:
    true_gate_set = noisy_bloch_gate_set()
    sequences = make_gst_sequences(max_repeat=4)
    dataset = simulate_dataset(true_gate_set, sequences, shots=1_000_000, seed=2)
    dataset = type(dataset)(
        sequences=dataset.sequences,
        probabilities=sequence_probabilities(true_gate_set, sequences),
        counts=dataset.counts,
        shots=dataset.shots,
    )
    fit = fit_gate_set_model(dataset, max_iter=120)

    assert fit.rmse < 1e-6


def test_gst_prediction_beats_gate_only_on_spam_biased_data() -> None:
    true_gate_set = noisy_bloch_gate_set()
    sequences = make_gst_sequences(max_repeat=8)
    train, test = split_train_test_sequences(sequences, heldout_min_length=10)
    train_data = simulate_dataset(true_gate_set, train, shots=4096, seed=3)
    test_data = simulate_dataset(true_gate_set, test, shots=4096, seed=4)

    gate_only = fit_gate_only_model(train_data, max_iter=120)
    gst = fit_gate_set_model(train_data, max_iter=180)

    assert prediction_rmse(gst.gate_set, test_data) <= prediction_rmse(gate_only.gate_set, test_data)
