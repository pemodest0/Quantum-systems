from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.open_systems.noise_filtering import cpmg_sequence, filter_function
from oqs_control.open_systems.noise_spectroscopy import (
    fit_power_law_from_points,
    flux_qubit_like_spectrum,
    peak_approximation_points,
    simulate_coherences,
)


PAPER_ID = "flux_qubit_noise_spectroscopy_2011"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Noise spectroscopy through dynamical decoupling with a superconducting flux qubit",
    "venue": "Nature Physics",
    "year": 2011,
    "doi": "10.1038/nphys1994",
    "role": "flux_qubit_dd_noise_spectroscopy",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_flux_spectrum_points(path: Path, omega: np.ndarray, spectrum: np.ndarray, points) -> None:
    freq_hz = omega / (2.0 * np.pi)
    point_freq = np.array([point.frequency_hz for point in points], dtype=float)
    point_spec = np.array([point.spectrum_estimate for point in points], dtype=float)
    fig, ax = plt.subplots(figsize=(8.6, 5.1), constrained_layout=True)
    ax.loglog(freq_hz, spectrum, label="true synthetic 1/f^alpha spectrum")
    ax.scatter(point_freq, point_spec, color="tab:red", zorder=5, label="DD peak estimates")
    ax.set_title("Flux-qubit-style noise spectroscopy by CPMG peak sampling")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("S(omega), arb.")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_coherence_vs_pulse_count(path: Path, points) -> None:
    pulse_counts = np.array([point.pulse_count for point in points], dtype=int)
    coherence = np.array([point.coherence for point in points], dtype=float)
    fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    ax.plot(pulse_counts, coherence, marker="o")
    ax.set_title("CPMG coherence under synthetic flux-qubit noise")
    ax.set_xlabel("number of pi pulses")
    ax.set_ylabel("coherence")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_filter_peak_map(path: Path, omega: np.ndarray, sequences) -> None:
    freq_hz = omega / (2.0 * np.pi)
    fig, ax = plt.subplots(figsize=(8.7, 5.1), constrained_layout=True)
    for sequence in sequences:
        filt = filter_function(omega, sequence, n_time_samples=1536)
        normalized = filt / max(float(np.max(filt)), 1e-30)
        ax.loglog(freq_hz, normalized, label=sequence.name)
    ax.set_title("CPMG filter peaks move with pulse count")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("normalized filter")
    ax.grid(alpha=0.25, which="both")
    ax.legend(ncols=2, fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_power_law_fit(path: Path, points, fit: dict[str, float]) -> None:
    freq = np.array([point.frequency_hz for point in points], dtype=float)
    spec = np.array([point.spectrum_estimate for point in points], dtype=float)
    fitted = fit["amplitude_at_1mhz"] * (1.0e6 / freq) ** fit["alpha"]
    fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    ax.loglog(freq, spec, marker="o", ls="", label="DD estimates")
    ax.loglog(freq, fitted, label=f"fit alpha={fit['alpha']:.3f}")
    ax.set_title("Power-law fit from DD noise spectroscopy")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("S(omega), arb.")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    true_alpha = 0.78
    total_time_s = 4.0e-6
    omega = np.linspace(2.0 * np.pi * 0.1e6, 2.0 * np.pi * 18.0e6, 1500)
    true_spectrum = flux_qubit_like_spectrum(
        omega,
        amplitude=3.0e4,
        alpha=true_alpha,
        white_floor=100.0,
    )
    pulse_counts = (2, 4, 6, 8, 12, 16, 24, 32, 48, 64)
    sequences = tuple(cpmg_sequence(total_time_s, count) for count in pulse_counts)
    points = peak_approximation_points(omega, true_spectrum, sequences, n_time_samples=1536)
    fit = fit_power_law_from_points(points)
    coherence, _ = simulate_coherences(omega, true_spectrum, sequences, n_time_samples=1536)

    figures = {
        "flux_spectrum_peak_estimates": figure_dir / "flux_spectrum_peak_estimates.png",
        "flux_coherence_vs_pulse_count": figure_dir / "flux_coherence_vs_pulse_count.png",
        "flux_filter_peak_map": figure_dir / "flux_filter_peak_map.png",
        "flux_power_law_fit": figure_dir / "flux_power_law_fit.png",
    }
    plot_flux_spectrum_points(figures["flux_spectrum_peak_estimates"], omega, true_spectrum, points)
    plot_coherence_vs_pulse_count(figures["flux_coherence_vs_pulse_count"], points)
    plot_filter_peak_map(figures["flux_filter_peak_map"], omega, sequences)
    plot_power_law_fit(figures["flux_power_law_fit"], points, fit)

    point_rows = [
        {
            "sequence": point.sequence,
            "pulse_count": point.pulse_count,
            "frequency_hz": point.frequency_hz,
            "spectrum_estimate": point.spectrum_estimate,
            "coherence": point.coherence,
            "chi": point.chi,
        }
        for point in points
    ]
    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "flux_qubit_dd_noise_spectroscopy",
        "simulation": {
            "total_time_s": total_time_s,
            "true_alpha": true_alpha,
            "frequency_min_hz": float(omega[0] / (2.0 * np.pi)),
            "frequency_max_hz": float(omega[-1] / (2.0 * np.pi)),
            "pulse_counts": list(pulse_counts),
        },
        "spectroscopy_summary": {
            "estimated_alpha": fit["alpha"],
            "alpha_abs_error": float(abs(fit["alpha"] - true_alpha)),
            "amplitude_at_1mhz": fit["amplitude_at_1mhz"],
            "rmse_log": fit["rmse_log"],
            "min_coherence": float(np.min(coherence)),
            "max_coherence": float(np.max(coherence)),
        },
        "peak_points": point_rows,
        "scientific_interpretation": {
            "captures": [
                "CPMG pulse count maps coherence decay to spectral samples",
                "peak-filter approximation gives a direct frequency-domain noise estimate",
                "a power-law noise exponent can be extracted from DD data",
                "the method is directly relevant for hardware noise diagnosis",
            ],
            "does_not_capture": [
                "no superconducting flux-qubit hardware data are reproduced",
                "finite pulse width and pulse imperfections are neglected",
                "the spectral estimator uses the simple peak approximation rather than full experimental calibration",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "coherence": "C_N(T) = exp[- integral S(omega) F_N(omega) d omega / pi]",
            "peak_approximation": "S(omega_peak) approx chi_N / area(F_N)",
            "power_law": "S(f) = A (1 MHz / f)^alpha",
        },
        "assumptions": [
            "The benchmark uses a synthetic flux-qubit-like 1/f^alpha spectrum.",
            "CPMG pulses are instantaneous and ideal.",
            "The result is a noise-spectroscopy workflow reproduction, not a hardware-data reproduction.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": metrics["spectroscopy_summary"],
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# Flux-Qubit Noise Spectroscopy Through Dynamical Decoupling",
                "",
                "This run reconstructs a synthetic power-law dephasing spectrum",
                "from CPMG coherence data using the filter-peak approximation.",
                "",
                f"True alpha: `{true_alpha:.6f}`.",
                f"Estimated alpha: `{fit['alpha']:.6f}`.",
                f"Alpha absolute error: `{abs(fit['alpha'] - true_alpha):.6f}`.",
                f"Minimum coherence: `{float(np.min(coherence)):.8f}`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the flux-qubit noise spectroscopy Paper O target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
