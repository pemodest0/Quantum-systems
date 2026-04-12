from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.hardware.gate_set_tomography import (
    fit_gate_only_model,
    fit_gate_set_model,
    gate_matrix_error,
    ideal_bloch_gate_set,
    make_gst_sequences,
    noisy_bloch_gate_set,
    prediction_rmse,
    rmse_by_length,
    sequence_probabilities,
    sequence_to_label,
    simulate_dataset,
    spam_error,
    split_train_test_sequences,
)


PAPER_ID = "gate_set_tomography_2021"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Gate Set Tomography",
    "venue": "Quantum",
    "year": 2021,
    "doi": "10.22331/q-2021-10-05-557",
    "role": "spam_aware_hardware_characterization",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_prediction_by_length(
    path: Path,
    gate_only_rows: list[dict[str, float]],
    gst_rows: list[dict[str, float]],
) -> None:
    go = {int(row["length"]): row for row in gate_only_rows}
    gs = {int(row["length"]): row for row in gst_rows}
    lengths = np.array(sorted(set(go) | set(gs)), dtype=int)
    go_rmse = np.array([go.get(int(length), {"rmse": np.nan})["rmse"] for length in lengths], dtype=float)
    gs_rmse = np.array([gs.get(int(length), {"rmse": np.nan})["rmse"] for length in lengths], dtype=float)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), constrained_layout=True)
    ax.semilogy(lengths, go_rmse, marker="o", label="gate-only fit, ideal SPAM")
    ax.semilogy(lengths, gs_rmse, marker="s", label="GST fit")
    ax.set_title("Prediction residuals by sequence length")
    ax.set_xlabel("sequence length")
    ax.set_ylabel("probability RMSE")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_heldout_predictions(
    path: Path,
    measured: np.ndarray,
    gate_only: np.ndarray,
    gst: np.ndarray,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.7), constrained_layout=True)
    for ax, predicted, title in (
        (axes[0], gate_only, "gate-only, ideal SPAM"),
        (axes[1], gst, "GST self-consistent"),
    ):
        ax.scatter(measured, predicted, s=18, alpha=0.75)
        ax.plot([0, 1], [0, 1], color="0.25", ls="--", lw=1.0)
        ax.set_title(title)
        ax.set_xlabel("heldout measured probability")
        ax.set_ylabel("model prediction")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_gauge_dependent_spam(
    path: Path,
    true_gate_set,
    ideal_gate_set,
    gst_gate_set,
) -> None:
    labels = ["prep_x", "prep_y", "prep_z", "eff_0", "eff_x", "eff_y", "eff_z"]
    true = np.concatenate([true_gate_set.prep, true_gate_set.effect])
    ideal = np.concatenate([ideal_gate_set.prep, ideal_gate_set.effect])
    gst = np.concatenate([gst_gate_set.prep, gst_gate_set.effect])
    x = np.arange(len(labels))
    width = 0.26

    fig, ax = plt.subplots(figsize=(9.2, 5.0), constrained_layout=True)
    ax.bar(x - width, true, width=width, label="simulation truth")
    ax.bar(x, ideal, width=width, label="ideal assumption")
    ax.bar(x + width, gst, width=width, label="GST optimizer gauge")
    ax.set_title("SPAM parameters are gauge-dependent")
    ax.set_ylabel("parameter value")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_gate_matrix_residuals(path: Path, true_gate_set, gate_only_set, gst_set) -> None:
    matrices = [
        ("Gx true", true_gate_set.gates["x"]),
        ("Gx gate-only - true", gate_only_set.gates["x"] - true_gate_set.gates["x"]),
        ("Gx GST - true", gst_set.gates["x"] - true_gate_set.gates["x"]),
        ("Gy true", true_gate_set.gates["y"]),
        ("Gy gate-only - true", gate_only_set.gates["y"] - true_gate_set.gates["y"]),
        ("Gy GST - true", gst_set.gates["y"] - true_gate_set.gates["y"]),
    ]
    vmax = max(float(np.max(np.abs(matrix))) for _, matrix in matrices)
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.4), constrained_layout=True)
    for ax, (title, matrix) in zip(axes.ravel(), matrices):
        image = ax.imshow(matrix, vmin=-vmax, vmax=vmax, cmap="coolwarm")
        ax.set_title(title, fontsize=9)
        ax.set_xticks(range(3), ["X", "Y", "Z"])
        ax.set_yticks(range(3), ["X", "Y", "Z"])
    fig.colorbar(image, ax=axes, shrink=0.85)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def longest_sequence_rows(test_data, gate_only_set, gst_set, count: int = 12) -> list[dict[str, float | str]]:
    predicted_gate_only = sequence_probabilities(gate_only_set, test_data.sequences)
    predicted_gst = sequence_probabilities(gst_set, test_data.sequences)
    order = np.argsort([-len(sequence) for sequence in test_data.sequences])
    rows: list[dict[str, float | str]] = []
    for idx in order[:count]:
        sequence = test_data.sequences[int(idx)]
        rows.append(
            {
                "sequence": sequence_to_label(sequence),
                "length": int(len(sequence)),
                "measured": float(test_data.probabilities[int(idx)]),
                "gate_only_prediction": float(predicted_gate_only[int(idx)]),
                "gst_prediction": float(predicted_gst[int(idx)]),
                "gate_only_abs_error": float(abs(predicted_gate_only[int(idx)] - test_data.probabilities[int(idx)])),
                "gst_abs_error": float(abs(predicted_gst[int(idx)] - test_data.probabilities[int(idx)])),
            }
        )
    return rows


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    true_gate_set = noisy_bloch_gate_set()
    ideal_gate_set = ideal_bloch_gate_set()
    sequences = make_gst_sequences(max_repeat=16)
    train_sequences, test_sequences = split_train_test_sequences(sequences, heldout_min_length=20)
    shots = 4096
    train_data = simulate_dataset(true_gate_set, train_sequences, shots=shots, seed=701)
    test_data = simulate_dataset(true_gate_set, test_sequences, shots=shots, seed=702)

    gate_only = fit_gate_only_model(train_data, initial=ideal_gate_set, max_iter=400)
    gst = fit_gate_set_model(train_data, initial=ideal_gate_set, max_iter=700)

    train_rmse_gate_only = prediction_rmse(gate_only.gate_set, train_data)
    train_rmse_gst = prediction_rmse(gst.gate_set, train_data)
    test_rmse_gate_only = prediction_rmse(gate_only.gate_set, test_data)
    test_rmse_gst = prediction_rmse(gst.gate_set, test_data)

    gate_only_length_rows = rmse_by_length(gate_only.gate_set, test_data)
    gst_length_rows = rmse_by_length(gst.gate_set, test_data)
    measured_test = test_data.probabilities
    gate_only_pred = sequence_probabilities(gate_only.gate_set, test_data.sequences)
    gst_pred = sequence_probabilities(gst.gate_set, test_data.sequences)

    figures = {
        "gst_prediction_by_sequence_length": figure_dir / "gst_prediction_by_sequence_length.png",
        "gst_heldout_predictions": figure_dir / "gst_heldout_predictions.png",
        "gst_gauge_dependent_spam": figure_dir / "gst_gauge_dependent_spam.png",
        "gst_gate_matrix_residuals": figure_dir / "gst_gate_matrix_residuals.png",
    }
    plot_prediction_by_length(figures["gst_prediction_by_sequence_length"], gate_only_length_rows, gst_length_rows)
    plot_heldout_predictions(figures["gst_heldout_predictions"], measured_test, gate_only_pred, gst_pred)
    plot_gauge_dependent_spam(figures["gst_gauge_dependent_spam"], true_gate_set, ideal_gate_set, gst.gate_set)
    plot_gate_matrix_residuals(figures["gst_gate_matrix_residuals"], true_gate_set, gate_only.gate_set, gst.gate_set)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "gate_set_tomography",
        "dataset": {
            "shots": shots,
            "total_sequence_count": len(sequences),
            "train_sequence_count": len(train_sequences),
            "heldout_sequence_count": len(test_sequences),
            "max_sequence_length": max(len(sequence) for sequence in sequences),
            "heldout_min_length": min(len(sequence) for sequence in test_sequences),
        },
        "prediction_summary": {
            "train_rmse_gate_only_ideal_spam": train_rmse_gate_only,
            "train_rmse_gst": train_rmse_gst,
            "heldout_rmse_gate_only_ideal_spam": test_rmse_gate_only,
            "heldout_rmse_gst": test_rmse_gst,
            "heldout_improvement_factor": float(test_rmse_gate_only / max(test_rmse_gst, 1e-15)),
        },
        "fit_summary": {
            "gate_only_success": gate_only.success,
            "gate_only_iterations": gate_only.iterations,
            "gst_success": gst.success,
            "gst_iterations": gst.iterations,
            "note": "Direct gate/SPAM parameter errors are gauge-dependent; predictive probabilities are the primary gauge-invariant comparison.",
        },
        "gauge_dependent_diagnostics": {
            "gate_only_gate_matrix_error_to_simulation_gauge": gate_matrix_error(gate_only.gate_set, true_gate_set),
            "gst_gate_matrix_error_to_simulation_gauge": gate_matrix_error(gst.gate_set, true_gate_set),
            "ideal_spam_error_to_simulation_gauge": spam_error(ideal_gate_set, true_gate_set),
            "gst_spam_error_to_simulation_gauge": spam_error(gst.gate_set, true_gate_set),
        },
        "heldout_long_sequence_examples": longest_sequence_rows(test_data, gate_only.gate_set, gst.gate_set),
        "heldout_rmse_by_length": {
            "gate_only_ideal_spam": gate_only_length_rows,
            "gst": gst_length_rows,
        },
        "scientific_interpretation": {
            "captures": [
                "GST estimates state preparation, measurement, and gates self-consistently",
                "long sequences amplify coherent gate errors and improve predictive sensitivity",
                "ideal-SPAM gate-only fitting misattributes SPAM error to gates",
                "predictive probabilities are the safest comparison because GST has gauge freedom",
            ],
            "does_not_capture": [
                "no pyGSTi long-sequence GST implementation is reproduced",
                "no full gauge-optimization or confidence-region analysis is implemented",
                "the model is single-qubit and unital in the gate block",
                "the benchmark is synthetic and does not use real hardware counts",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "sequence_probability": "p_s = e dot G_s rho",
            "gate_only_fit": "min sum_s (p_s(Gx,Gy; ideal rho,e) - f_s)^2",
            "gst_fit": "min sum_s (p_s(Gx,Gy,rho,e) - f_s)^2",
            "long_sequence_amplification": "sequences include repeated germs up to length 80",
        },
        "assumptions": [
            "The reproduction implements a minimal single-qubit GST-like estimator, not pyGSTi.",
            "Gates are represented by unital 3x3 Bloch matrices.",
            "State preparation and measurement are represented by a Bloch vector and measurement effect vector.",
            "No explicit gauge fixing is applied; prediction error is the primary comparison.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "train_rmse_gate_only_ideal_spam": train_rmse_gate_only,
            "train_rmse_gst": train_rmse_gst,
            "heldout_rmse_gate_only_ideal_spam": test_rmse_gate_only,
            "heldout_rmse_gst": test_rmse_gst,
            "heldout_improvement_factor": metrics["prediction_summary"]["heldout_improvement_factor"],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the Gate Set Tomography Paper K target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

