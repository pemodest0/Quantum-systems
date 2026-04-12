from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oqs_control.workflows.experimental_decision_pipeline import (  # noqa: E402
    WORKFLOW_ID,
    ExperimentalDecisionConfig,
    config_to_json_dict,
    decisions_to_json,
    lab_manifest_template,
    run_pipeline,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_state_preparation(path: Path, target: np.ndarray, reconstructed: np.ndarray) -> None:
    vmax = max(float(np.max(np.abs(target))), float(np.max(np.abs(reconstructed))))
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.0), constrained_layout=True)
    for ax, matrix, title in zip(axes, (target, reconstructed), ("target |rho|", "QST reconstructed |rho|")):
        image = ax.imshow(np.abs(matrix), vmin=0.0, vmax=vmax, cmap="viridis")
        ax.set_title(title)
        ax.set_xlabel("column")
        ax.set_ylabel("row")
    fig.colorbar(image, ax=axes, shrink=0.82)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_spectrum(path: Path, omega: np.ndarray, true_spectrum: np.ndarray, reconstructed: np.ndarray) -> None:
    freq_hz = omega / (2.0 * np.pi)
    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.loglog(freq_hz, true_spectrum, label="synthetic true spectrum")
    ax.loglog(freq_hz, reconstructed, label="DD reconstructed spectrum")
    ax.set_title("Noise spectrum reconstructed from DD coherences")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("S(omega), arb.")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_spectroscopy_fit(
    path: Path,
    sequence_names: list[str],
    measured: np.ndarray,
    predicted: np.ndarray,
) -> None:
    x = np.arange(len(sequence_names))
    fig, ax = plt.subplots(figsize=(10.5, 5.0), constrained_layout=True)
    ax.plot(x, measured, marker="o", label="synthetic measured coherence")
    ax.plot(x, predicted, marker="s", label="predicted from reconstructed spectrum")
    ax.set_title("DD spectroscopy measurements and reconstructed-model fit")
    ax.set_ylabel("coherence")
    ax.set_xticks(x[::2], sequence_names[::2], rotation=35, ha="right")
    ax.set_ylim(0.82, 1.01)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_control_decision(path: Path, decisions: list[dict[str, float | int | str]], selected_sequence: str) -> None:
    labels = [str(row["sequence"]) for row in decisions]
    predicted = np.array([float(row["predicted_coherence"]) for row in decisions], dtype=float)
    true_values = np.array([float(row["synthetic_true_coherence"]) for row in decisions], dtype=float)
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(11.0, 5.2), constrained_layout=True)
    ax.bar(x - 0.18, predicted, width=0.36, label="predicted")
    ax.bar(x + 0.18, true_values, width=0.36, label="synthetic truth")
    selected_index = labels.index(selected_sequence)
    ax.axvline(selected_index, color="0.1", linestyle="--", lw=1.1, label="selected")
    ax.set_title("Control-sequence decision from reconstructed noise")
    ax.set_ylabel("coherence after sequence")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.2, axis="y")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path, lab_manifest: Path | None = None) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = ExperimentalDecisionConfig()
    result = run_pipeline(config=config, lab_manifest_path=lab_manifest)
    decisions = decisions_to_json(result.candidate_decisions)
    selected = asdict(result.selected_sequence)
    state = result.state_preparation
    reconstruction = result.reconstruction
    sequence_names = [sequence.name for sequence in result.spectroscopy_sequences]

    figures = {
        "state_preparation": str(figure_dir / "state_preparation_qst.png"),
        "noise_spectrum": str(figure_dir / "reconstructed_noise_spectrum.png"),
        "spectroscopy_fit": str(figure_dir / "dd_spectroscopy_fit.png"),
        "control_decision": str(figure_dir / "control_sequence_decision.png"),
    }
    plot_state_preparation(
        Path(figures["state_preparation"]),
        state.target_state,
        state.reconstructed_state,
    )
    plot_spectrum(
        Path(figures["noise_spectrum"]),
        result.omega_rad_s,
        result.true_spectrum,
        reconstruction.reconstructed_spectrum,
    )
    plot_spectroscopy_fit(
        Path(figures["spectroscopy_fit"]),
        sequence_names,
        result.measured_coherence,
        reconstruction.predicted_coherence,
    )
    plot_control_decision(
        Path(figures["control_decision"]),
        decisions,
        result.selected_sequence.sequence,
    )

    metrics = {
        "workflow_id": WORKFLOW_ID,
        "status": "completed",
        "benchmark_type": "experimental_decision_pipeline",
        "state_preparation_summary": {
            "qst_fidelity": state.fidelity,
            "frobenius_error": state.frobenius_error,
            "tomography_residual_norm": state.tomography_residual_norm,
            "prepared_coherence_norm": state.prepared_coherence_norm,
        },
        "spectroscopy_summary": {
            "sequence_count": len(result.spectroscopy_sequences),
            "spectrum_correlation": reconstruction.correlation,
            "relative_spectrum_error": reconstruction.relative_error,
            "residual_norm": reconstruction.residual_norm,
            "mean_abs_coherence_fit_error": float(
                np.mean(np.abs(reconstruction.predicted_coherence - result.measured_coherence))
            ),
        },
        "decision_summary": {
            "candidate_count": len(decisions),
            "selected_sequence": result.selected_sequence.sequence,
            "selected_pulse_count": result.selected_sequence.pulse_count,
            "selected_filter_peak_hz": result.selected_sequence.filter_peak_hz,
            "selected_predicted_coherence": result.selected_sequence.predicted_coherence,
            "selected_synthetic_true_coherence": result.selected_sequence.synthetic_true_coherence,
            "selected_prediction_error": result.selected_sequence.prediction_error,
        },
        "candidate_decisions": decisions,
        "lab_comparison": asdict(result.lab_comparison),
        "figures": figures,
    }
    config_used = {
        "workflow_id": WORKFLOW_ID,
        "config": config_to_json_dict(config),
        "lab_manifest": str(lab_manifest) if lab_manifest is not None else None,
        "implemented_steps": {
            "state_preparation": "synthetic spin-3/2 target state + 7-phase QST reconstruction",
            "spectroscopy": "DD coherence measurements generated from a colored dephasing spectrum",
            "spectrum_reconstruction": "chi_i = -log(C_i), NNLS with S(omega) >= 0",
            "control_decision": "candidate sequence with maximal predicted coherence is selected",
            "lab_comparison": "optional manifest residuals compare predicted and measured coherences",
        },
        "assumptions": [
            "The current run is synthetic because incoming raw lab data are not available yet.",
            "DD pulses are ideal and instantaneous.",
            "The coherence model is pure dephasing and does not yet include pulse imperfections.",
            "QST is used as a preparation/readout consistency check, not as a full experimental calibration.",
        ],
    }
    results = {
        "workflow_id": WORKFLOW_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "selected_sequence": selected,
        "summary": {
            "qst_fidelity": state.fidelity,
            "spectrum_correlation": reconstruction.correlation,
            "selected_sequence": result.selected_sequence.sequence,
            "selected_predicted_coherence": result.selected_sequence.predicted_coherence,
            "lab_comparison_status": result.lab_comparison.status,
        },
        "figures": figures,
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    write_json(output_dir / "lab_manifest_template.json", lab_manifest_template())

    run_metadata = {
        "workflow_id": WORKFLOW_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics_sha256": sha256_file(output_dir / "metrics.json"),
        "config_used_sha256": sha256_file(output_dir / "config_used.json"),
        "results_sha256": sha256_file(output_dir / "results.json"),
    }
    write_json(output_dir / "run_metadata.json", run_metadata)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the experimental decision pipeline workflow.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "workflows" / WORKFLOW_ID / "latest",
    )
    parser.add_argument("--lab-manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    results = run(args.output_dir, lab_manifest=args.lab_manifest)
    print(json.dumps({"workflow_id": WORKFLOW_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
