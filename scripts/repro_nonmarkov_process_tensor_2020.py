from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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
    sequence_probability,
    sequence_to_label,
    simulate_process_tensor_dataset,
)


PAPER_ID = "nonmarkov_process_tensor_2020"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Demonstration of non-Markovian process characterisation and control on a quantum processor",
    "venue": "Nature Communications",
    "year": 2020,
    "doi": "10.1038/s41467-020-20113-3",
    "role": "process_tensor_memory_characterization",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def sequence_bank(max_length: int = 3) -> tuple[tuple[str, ...], ...]:
    controls = ("i", "x", "y", "x2", "y2")
    sequences: list[tuple[str, ...]] = []
    for length in range(1, int(max_length) + 1):
        sequences.extend(make_control_sequences(length, controls=controls))
    return tuple(sequences)


def process_tensor_predictions(characterization, validation) -> np.ndarray:
    lookup = {
        sequence: probability
        for sequence, probability in zip(characterization.sequences, characterization.probabilities)
    }
    return np.array([lookup[sequence] for sequence in validation.sequences], dtype=float)


def markovian_predictions(sequences, fit) -> np.ndarray:
    return np.array([markovian_prediction(sequence, fit.lambda_xy) for sequence in sequences], dtype=float)


def rmse_by_length(validation, process_pred: np.ndarray, markov_pred: np.ndarray) -> list[dict[str, float]]:
    lengths = np.array([len(sequence) for sequence in validation.sequences], dtype=int)
    rows: list[dict[str, float]] = []
    for length in sorted(set(lengths)):
        mask = lengths == length
        measured = validation.probabilities[mask]
        rows.append(
            {
                "length": int(length),
                "count": int(np.count_nonzero(mask)),
                "process_tensor_rmse": float(np.sqrt(np.mean((process_pred[mask] - measured) ** 2))),
                "markovian_rmse": float(np.sqrt(np.mean((markov_pred[mask] - measured) ** 2))),
            }
        )
    return rows


def top_sequence_rows(dataset, config: CorrelatedDephasingConfig, count: int = 12) -> list[dict[str, float | str]]:
    order = np.argsort(-dataset.probabilities)
    rows: list[dict[str, float | str]] = []
    for idx in order[:count]:
        sequence = dataset.sequences[int(idx)]
        rows.append(
            {
                "sequence": sequence_to_label(sequence),
                "length": int(len(sequence)),
                "characterized_probability": float(dataset.probabilities[int(idx)]),
                "true_probability": float(sequence_probability(sequence, config)),
            }
        )
    return rows


def plot_prediction_scatter(path: Path, measured: np.ndarray, process_pred: np.ndarray, markov_pred: np.ndarray) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.7), constrained_layout=True)
    for ax, predicted, title in (
        (axes[0], markov_pred, "Markovian one-step channel"),
        (axes[1], process_pred, "Process tensor lookup"),
    ):
        ax.scatter(measured, predicted, s=18, alpha=0.75)
        ax.plot([0, 1], [0, 1], color="0.25", ls="--", lw=1.0)
        ax.set_title(title)
        ax.set_xlabel("validation probability")
        ax.set_ylabel("prediction")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_rmse_by_length(path: Path, rows: list[dict[str, float]]) -> None:
    lengths = np.array([row["length"] for row in rows], dtype=int)
    process = np.array([row["process_tensor_rmse"] for row in rows], dtype=float)
    markov = np.array([row["markovian_rmse"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(7.8, 4.8), constrained_layout=True)
    ax.semilogy(lengths, markov, marker="o", label="Markovian")
    ax.semilogy(lengths, process, marker="s", label="process tensor")
    ax.set_title("Prediction error grows with history length for Markovian model")
    ax.set_xlabel("control-sequence length")
    ax.set_ylabel("validation RMSE")
    ax.set_xticks(lengths)
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_echo_witness(path: Path, config: CorrelatedDephasingConfig, fit) -> None:
    sequences = [("i",), ("x",), ("i", "i"), ("x", "x"), ("i", "x", "i"), ("x", "i", "x")]
    labels = [sequence_to_label(sequence) for sequence in sequences]
    true = np.array([sequence_probability(sequence, config) for sequence in sequences], dtype=float)
    markov = np.array([markovian_prediction(sequence, fit.lambda_xy) for sequence in sequences], dtype=float)
    x = np.arange(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8.8, 5.0), constrained_layout=True)
    ax.bar(x - width / 2.0, true, width=width, label="correlated-memory process")
    ax.bar(x + width / 2.0, markov, width=width, label="Markovian fitted channel")
    ax.set_title("Control-history witness: echo-like sequences recover coherence")
    ax.set_ylabel("P(+X)")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_control_landscape(path: Path, rows: list[dict[str, float | str]]) -> None:
    labels = [str(row["sequence"]) for row in rows]
    values = np.array([float(row["true_probability"]) for row in rows], dtype=float)
    x = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(10.2, 4.9), constrained_layout=True)
    ax.bar(x, values, color="tab:blue")
    ax.set_title("Top process-tensor-selected control sequences")
    ax.set_ylabel("true P(+X)")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = CorrelatedDephasingConfig(phase_rad=0.72, p_stay=0.92, shots=4096)
    sequences = sequence_bank(max_length=3)
    characterization = simulate_process_tensor_dataset(sequences, config, seed=1101)
    validation = simulate_process_tensor_dataset(sequences, config, seed=1102)
    markov_fit = fit_markovian_channel(characterization)

    process_pred = process_tensor_predictions(characterization, validation)
    markov_pred = markovian_predictions(validation.sequences, markov_fit)
    process_rmse = prediction_rmse_process_tensor(characterization, validation)
    markov_rmse = prediction_rmse_markovian(validation, markov_fit)
    length_rows = rmse_by_length(validation, process_pred, markov_pred)
    witness = process_tensor_memory_witness(characterization)

    process_best_seq, process_best_pred = best_sequence_from_dataset(characterization)
    markov_best_seq, markov_best_pred = best_sequence_markovian(sequences, markov_fit)
    top_rows = top_sequence_rows(characterization, config)
    process_best_true = sequence_probability(process_best_seq, config)
    markov_best_true = sequence_probability(markov_best_seq, config)

    figures = {
        "process_tensor_prediction_scatter": figure_dir / "process_tensor_prediction_scatter.png",
        "process_tensor_rmse_by_length": figure_dir / "process_tensor_rmse_by_length.png",
        "process_tensor_echo_witness": figure_dir / "process_tensor_echo_witness.png",
        "process_tensor_control_landscape": figure_dir / "process_tensor_control_landscape.png",
    }
    plot_prediction_scatter(figures["process_tensor_prediction_scatter"], validation.probabilities, process_pred, markov_pred)
    plot_rmse_by_length(figures["process_tensor_rmse_by_length"], length_rows)
    plot_echo_witness(figures["process_tensor_echo_witness"], config, markov_fit)
    plot_control_landscape(figures["process_tensor_control_landscape"], top_rows)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "process_tensor_nonmarkovian_control",
        "model": {
            "phase_rad_per_interval": config.phase_rad,
            "p_stay": config.p_stay,
            "shots": config.shots,
            "sequence_count": len(sequences),
            "controls": ["i", "x", "y", "x2", "y2"],
            "max_sequence_length": 3,
        },
        "prediction_summary": {
            "process_tensor_validation_rmse": process_rmse,
            "markovian_validation_rmse": markov_rmse,
            "improvement_factor": float(markov_rmse / max(process_rmse, 1e-15)),
            "markovian_lambda_xy": markov_fit.lambda_xy,
            "markovian_train_rmse": markov_fit.train_rmse,
        },
        "memory_witness": witness,
        "control_summary": {
            "process_tensor_best_sequence": sequence_to_label(process_best_seq),
            "process_tensor_predicted_probability": process_best_pred,
            "process_tensor_true_probability": process_best_true,
            "markovian_best_sequence": sequence_to_label(markov_best_seq),
            "markovian_predicted_probability": markov_best_pred,
            "markovian_true_probability": markov_best_true,
            "true_control_advantage": float(process_best_true - markov_best_true),
        },
        "rmse_by_length": length_rows,
        "top_process_tensor_sequences": top_rows,
        "scientific_interpretation": {
            "captures": [
                "a multi-time process tensor predicts control-sequence outcomes better than a fixed Markovian channel",
                "correlated phase noise creates history-dependent echo-like control benefits",
                "control can be selected from characterized multi-time data instead of a one-step channel",
                "the benchmark separates memory characterization from ordinary QPT",
            ],
            "does_not_capture": [
                "no IBM hardware run is reproduced",
                "the Choi-state process tensor reconstruction is represented operationally as a sequence table",
                "no over-complete dual-set reconstruction or maximum-likelihood estimator is implemented",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "process_tensor_action": "rho_k(A_{k-1:0}) = T^{k:0}[A_{k-1:0}]",
            "operational_table": "p(sequence) measured for a basis of multi-time interventions",
            "markovian_baseline": "single fitted channel M(lambda) repeated between controls",
            "control_selection": "argmax_sequence p_process_tensor(sequence)",
        },
        "assumptions": [
            "The process tensor is represented as an operational table over a finite control alphabet.",
            "The environment is a classical hidden two-state detuning with temporal persistence.",
            "The benchmark measures +X survival after control sequences.",
            "This is a synthetic memory/control benchmark, not a real-device reconstruction.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "process_tensor_validation_rmse": process_rmse,
            "markovian_validation_rmse": markov_rmse,
            "improvement_factor": metrics["prediction_summary"]["improvement_factor"],
            "process_tensor_best_sequence": metrics["control_summary"]["process_tensor_best_sequence"],
            "markovian_best_sequence": metrics["control_summary"]["markovian_best_sequence"],
            "true_control_advantage": metrics["control_summary"]["true_control_advantage"],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the non-Markovian process tensor Paper L target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

