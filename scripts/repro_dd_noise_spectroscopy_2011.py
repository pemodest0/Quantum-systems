from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.open_systems.noise_filtering import cpmg_sequence, udd_sequence
from oqs_control.open_systems.noise_spectroscopy import (
    add_coherence_noise,
    colored_noise_spectrum,
    reconstruct_spectrum_nnls,
    simulate_coherences,
)


PAPER_ID = "dd_noise_spectroscopy_2011"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Measuring the spectrum of colored noise by dynamical decoupling",
    "venue": "Physical Review Letters",
    "year": 2011,
    "doi": "10.1103/PhysRevLett.107.230501",
    "role": "dd_noise_spectrum_reconstruction",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_spectrum_reconstruction(path: Path, omega: np.ndarray, true_spectrum: np.ndarray, reconstructed: np.ndarray) -> None:
    freq_hz = omega / (2.0 * np.pi)
    fig, ax = plt.subplots(figsize=(8.7, 5.1), constrained_layout=True)
    ax.loglog(freq_hz, true_spectrum, label="true synthetic spectrum")
    ax.loglog(freq_hz, reconstructed, label="NNLS reconstructed spectrum")
    ax.set_title("DD noise spectroscopy: colored spectrum reconstruction")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("S(omega), arb.")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_coherence_fit(path: Path, measured: np.ndarray, predicted: np.ndarray, sequences) -> None:
    labels = [sequence.name for sequence in sequences]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10.5, 5.0), constrained_layout=True)
    ax.plot(x, measured, marker="o", label="measured synthetic coherence")
    ax.plot(x, predicted, marker="s", label="coherence predicted by reconstructed spectrum")
    ax.set_title("Coherence data used for spectral inversion")
    ax.set_ylabel("coherence")
    ax.set_xticks(x[::2], labels[::2], rotation=35, ha="right")
    ax.set_ylim(0.82, 1.01)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_residual(path: Path, omega: np.ndarray, true_spectrum: np.ndarray, reconstructed: np.ndarray) -> None:
    freq_hz = omega / (2.0 * np.pi)
    residual = reconstructed - true_spectrum
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax.semilogx(freq_hz, residual)
    ax.axhline(0.0, color="0.25", lw=1.0)
    ax.set_title("Spectrum reconstruction residual")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("S_reconstructed - S_true")
    ax.grid(alpha=0.25, which="both")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_sequence_sensitivity(path: Path, sequences, coherence: np.ndarray) -> None:
    pulse_counts = np.array([len(sequence.pulse_times_s) for sequence in sequences], dtype=int)
    is_cpmg = np.array([sequence.name.startswith("CPMG") for sequence in sequences])
    is_udd = np.array([sequence.name.startswith("UDD") for sequence in sequences])
    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.scatter(pulse_counts[is_cpmg], coherence[is_cpmg], label="CPMG", s=45)
    ax.scatter(pulse_counts[is_udd], coherence[is_udd], label="UDD", s=55)
    ax.set_title("Different DD sequences sample different spectral bands")
    ax.set_xlabel("number of pi pulses")
    ax.set_ylabel("synthetic coherence")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    total_time_s = 1.2e-3
    omega = np.linspace(2.0 * np.pi * 200.0, 2.0 * np.pi * 16.0e3, 180)
    true_spectrum = colored_noise_spectrum(
        omega,
        amplitude=60.0,
        peak_amplitude=42.0,
        white_floor=0.03,
        peak_center_hz=6.0e3,
        peak_width_hz=0.8e3,
    )
    sequences = tuple(cpmg_sequence(total_time_s, count) for count in range(1, 25))
    sequences += tuple(udd_sequence(total_time_s, count) for count in (2, 4, 6, 8, 10, 12))
    clean_coherence, _ = simulate_coherences(omega, true_spectrum, sequences, n_time_samples=768)
    measured_coherence = add_coherence_noise(clean_coherence, noise_std=0.003, seed=551)
    reconstruction = reconstruct_spectrum_nnls(
        omega,
        sequences,
        measured_coherence,
        smoothness=1e-3,
        n_time_samples=768,
        true_spectrum=true_spectrum,
    )

    figures = {
        "dd_reconstructed_spectrum": figure_dir / "dd_reconstructed_spectrum.png",
        "dd_coherence_fit": figure_dir / "dd_coherence_fit.png",
        "dd_spectrum_residual": figure_dir / "dd_spectrum_residual.png",
        "dd_sequence_sensitivity": figure_dir / "dd_sequence_sensitivity.png",
    }
    plot_spectrum_reconstruction(figures["dd_reconstructed_spectrum"], omega, true_spectrum, reconstruction.reconstructed_spectrum)
    plot_coherence_fit(figures["dd_coherence_fit"], measured_coherence, reconstruction.predicted_coherence, sequences)
    plot_residual(figures["dd_spectrum_residual"], omega, true_spectrum, reconstruction.reconstructed_spectrum)
    plot_sequence_sensitivity(figures["dd_sequence_sensitivity"], sequences, measured_coherence)

    peak_idx_true = int(np.argmax(true_spectrum))
    peak_idx_reconstructed = int(np.argmax(reconstruction.reconstructed_spectrum))
    freq_hz = omega / (2.0 * np.pi)
    feature_mask = (freq_hz >= 4.0e3) & (freq_hz <= 8.0e3)
    feature_indices = np.where(feature_mask)[0]
    feature_true_idx = int(feature_indices[np.argmax(true_spectrum[feature_mask])])
    feature_reconstructed_idx = int(feature_indices[np.argmax(reconstruction.reconstructed_spectrum[feature_mask])])
    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "dd_noise_spectrum_reconstruction",
        "simulation": {
            "total_time_s": total_time_s,
            "frequency_min_hz": float(omega[0] / (2.0 * np.pi)),
            "frequency_max_hz": float(omega[-1] / (2.0 * np.pi)),
            "sequence_count": len(sequences),
            "coherence_noise_std": 0.003,
        },
        "reconstruction_summary": {
            "relative_spectrum_error": reconstruction.relative_error,
            "spectrum_correlation": reconstruction.correlation,
            "residual_norm": reconstruction.residual_norm,
            "true_peak_frequency_hz": float(omega[peak_idx_true] / (2.0 * np.pi)),
            "reconstructed_peak_frequency_hz": float(omega[peak_idx_reconstructed] / (2.0 * np.pi)),
            "true_narrow_feature_frequency_hz": float(omega[feature_true_idx] / (2.0 * np.pi)),
            "reconstructed_narrow_feature_frequency_hz": float(omega[feature_reconstructed_idx] / (2.0 * np.pi)),
            "mean_abs_coherence_error": float(np.mean(np.abs(reconstruction.predicted_coherence - measured_coherence))),
        },
        "scientific_interpretation": {
            "captures": [
                "DD coherences can be inverted into a colored noise spectrum",
                "different pulse counts and sequence families probe different spectral bands",
                "non-negative least squares imposes a physical non-negative spectrum",
                "a narrow spectral feature can be localized by DD data",
            ],
            "does_not_capture": [
                "the experiment-specific nuclear-spin implementation is not reproduced",
                "finite pulse errors and relaxation channels beyond pure dephasing are neglected",
                "the inversion is a transparent NNLS benchmark, not the full paper-specific estimator",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "coherence": "C_i = exp[- integral S(omega) F_i(omega) d omega / pi]",
            "inversion": "chi_i = -log(C_i) = sum_j A_ij S_j",
            "physical_constraint": "S_j >= 0 solved by NNLS",
        },
        "assumptions": [
            "The benchmark uses synthetic colored dephasing noise.",
            "The DD filter functions are generated from ideal instantaneous pi pulses.",
            "The frequency-domain spectrum is reconstructed on a fixed grid.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": metrics["reconstruction_summary"],
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# Measuring Colored Noise By Dynamical Decoupling",
                "",
                "This run reconstructs a synthetic colored dephasing spectrum from",
                "dynamical-decoupling coherence measurements.",
                "",
                f"Spectrum correlation: `{reconstruction.correlation:.8f}`.",
                f"Relative spectrum error: `{reconstruction.relative_error:.8f}`.",
                f"True peak frequency: `{metrics['reconstruction_summary']['true_peak_frequency_hz']:.3f} Hz`.",
                f"Reconstructed peak frequency: `{metrics['reconstruction_summary']['reconstructed_peak_frequency_hz']:.3f} Hz`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the DD noise spectroscopy Paper N target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
