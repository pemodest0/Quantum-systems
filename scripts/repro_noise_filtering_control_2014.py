from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.open_systems.noise_filtering import (
    PulseSequence,
    coherence_from_filter,
    composite_noise_spectrum,
    cpmg_sequence,
    filter_function,
    filter_peak_frequency,
    hahn_echo_sequence,
    ramsey_sequence,
    sequence_family,
    switching_function,
    udd_sequence,
)


PAPER_ID = "noise_filtering_control_2014"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Experimental noise filtering by quantum control",
    "venue": "Nature Physics",
    "year": 2014,
    "doi": "10.1038/nphys3115",
    "role": "dynamical_decoupling_noise_filtering",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def sequence_rows(
    omega: np.ndarray,
    spectrum: np.ndarray,
    sequences: tuple[PulseSequence, ...],
) -> list[dict[str, float | str | int]]:
    rows: list[dict[str, float | str | int]] = []
    ramsey_coherence = coherence_from_filter(omega, spectrum, sequences[0], n_time_samples=2048)
    for sequence in sequences:
        coherence = coherence_from_filter(omega, spectrum, sequence, n_time_samples=2048)
        peak_rad_s = filter_peak_frequency(omega, sequence, n_time_samples=2048)
        rows.append(
            {
                "sequence": sequence.name,
                "pulse_count": int(len(sequence.pulse_times_s)),
                "coherence": coherence,
                "chi": float(-np.log(max(coherence, 1e-300))),
                "coherence_gain_vs_ramsey": float(coherence / max(ramsey_coherence, 1e-300)),
                "filter_peak_hz": float(peak_rad_s / (2.0 * np.pi)),
            }
        )
    return rows


def plot_noise_and_filters(
    path: Path,
    omega: np.ndarray,
    spectrum: np.ndarray,
    sequences: tuple[PulseSequence, ...],
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 7.0), constrained_layout=True, sharex=True)
    freq_hz = omega / (2.0 * np.pi)
    axes[0].loglog(freq_hz, spectrum, color="0.2")
    axes[0].set_title("Synthetic dephasing noise spectrum")
    axes[0].set_ylabel("S(omega), arb.")
    axes[0].grid(alpha=0.25, which="both")
    for sequence in sequences:
        filt = filter_function(omega, sequence, n_time_samples=2048)
        normalized = filt / max(float(np.max(filt)), 1e-30)
        axes[1].loglog(freq_hz, normalized, label=sequence.name)
    axes[1].set_title("Normalized control filter functions")
    axes[1].set_xlabel("frequency (Hz)")
    axes[1].set_ylabel("normalized |Y(omega)|^2")
    axes[1].grid(alpha=0.25, which="both")
    axes[1].legend(ncols=2, fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_coherence_vs_pulses(path: Path, rows: list[dict[str, float | str | int]]) -> None:
    labels = [str(row["sequence"]) for row in rows]
    values = np.array([float(row["coherence"]) for row in rows], dtype=float)
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(8.8, 5.0), constrained_layout=True)
    ax.bar(x, values, color="tab:green")
    ax.set_title("Noise filtering improves coherence when filter avoids spectral weight")
    ax.set_ylabel("coherence exp[-chi]")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylim(0, 1.02)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_time_domain_switching(path: Path, sequences: tuple[PulseSequence, ...]) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.0), constrained_layout=True)
    for idx, sequence in enumerate(sequences):
        times = np.linspace(0.0, sequence.total_time_s, 700)
        y_t = switching_function(times, sequence)
        ax.plot(times * 1e3, y_t + 2.3 * idx, label=sequence.name)
    ax.set_title("Time-domain modulation functions y(t)")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("offset switching function")
    ax.set_yticks([])
    ax.grid(alpha=0.25)
    ax.legend(ncols=2, fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_peak_tracking(path: Path, total_time_s: float, omega: np.ndarray) -> list[dict[str, float]]:
    pulse_counts = np.array([1, 2, 4, 8, 12, 16], dtype=int)
    rows: list[dict[str, float]] = []
    for count in pulse_counts:
        cpmg = cpmg_sequence(total_time_s, int(count))
        udd = udd_sequence(total_time_s, int(count))
        rows.append(
            {
                "pulse_count": int(count),
                "cpmg_peak_hz": filter_peak_frequency(omega, cpmg, n_time_samples=2048) / (2.0 * np.pi),
                "udd_peak_hz": filter_peak_frequency(omega, udd, n_time_samples=2048) / (2.0 * np.pi),
            }
        )
    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    ax.plot(pulse_counts, [row["cpmg_peak_hz"] for row in rows], marker="o", label="CPMG")
    ax.plot(pulse_counts, [row["udd_peak_hz"] for row in rows], marker="s", label="UDD")
    ax.set_title("Filter peak frequency is tunable by pulse count")
    ax.set_xlabel("number of pi pulses")
    ax.set_ylabel("dominant filter peak (Hz)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return rows


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    total_time_s = 1.2e-3
    omega = np.linspace(2.0 * np.pi * 10.0, 2.0 * np.pi * 30.0e3, 1400)
    spectrum = composite_noise_spectrum(omega)
    sequences = (
        ramsey_sequence(total_time_s),
        hahn_echo_sequence(total_time_s),
        cpmg_sequence(total_time_s, 2),
        cpmg_sequence(total_time_s, 4),
        cpmg_sequence(total_time_s, 8),
        udd_sequence(total_time_s, 4),
        udd_sequence(total_time_s, 8),
    )
    rows = sequence_rows(omega, spectrum, sequences)

    figures = {
        "noise_spectrum_and_filters": figure_dir / "noise_spectrum_and_filters.png",
        "coherence_vs_control_sequence": figure_dir / "coherence_vs_control_sequence.png",
        "time_domain_switching_functions": figure_dir / "time_domain_switching_functions.png",
        "filter_peak_tracking": figure_dir / "filter_peak_tracking.png",
    }
    plot_noise_and_filters(figures["noise_spectrum_and_filters"], omega, spectrum, sequences)
    plot_coherence_vs_pulses(figures["coherence_vs_control_sequence"], rows)
    plot_time_domain_switching(figures["time_domain_switching_functions"], sequences)
    peak_rows = plot_peak_tracking(figures["filter_peak_tracking"], total_time_s, omega)

    best = max(rows, key=lambda row: float(row["coherence"]))
    ramsey = rows[0]
    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "quantum_control_noise_filtering",
        "simulation": {
            "total_time_s": total_time_s,
            "frequency_min_hz": float(omega[0] / (2.0 * np.pi)),
            "frequency_max_hz": float(omega[-1] / (2.0 * np.pi)),
            "sequence_count": len(sequences),
            "noise_model": "low-frequency Lorentzian plus narrow spectral peak near 4 kHz",
        },
        "sequence_table": rows,
        "filter_peak_tracking": peak_rows,
        "summary": {
            "ramsey_coherence": float(ramsey["coherence"]),
            "best_sequence": str(best["sequence"]),
            "best_coherence": float(best["coherence"]),
            "best_gain_vs_ramsey": float(best["coherence_gain_vs_ramsey"]),
            "best_filter_peak_hz": float(best["filter_peak_hz"]),
        },
        "scientific_interpretation": {
            "captures": [
                "control pulses define a modulation function y(t)",
                "the filter function |Y(omega)|^2 selects which spectral noise components cause dephasing",
                "changing pulse number moves filter peaks and changes coherence",
                "dynamical decoupling can act as both noise suppression and noise spectroscopy",
            ],
            "does_not_capture": [
                "no real qubit experimental data are used",
                "finite pulse width and pulse errors are neglected",
                "the filter function is computed numerically rather than using every analytic expression from the paper",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "modulation": "y(t) = +/- 1 with sign flips at pi pulses",
            "filter": "Y(omega) = integral_0^T y(t) exp(i omega t) dt",
            "dephasing": "chi(T) = integral S(omega) |Y(omega)|^2 d omega / pi",
            "coherence": "C(T) = exp[-chi(T)]",
        },
        "assumptions": [
            "The benchmark treats pure dephasing noise only.",
            "Pi pulses are instantaneous and ideal.",
            "The synthetic spectrum is chosen to show both low-frequency filtering and narrow-band sensitivity.",
            "This is a model reproduction, not a digitized experimental figure.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": metrics["summary"],
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the noise-filtering Paper M target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

