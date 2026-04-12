from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.hardware.multipass_qpt import (
    MultipassQPTConfig,
    ptm_frobenius_error,
    simulate_qpt_estimate,
    single_qubit_process,
)
from oqs_control.hardware.projected_qpt import (
    choi_frobenius_error,
    projected_least_squares_qpt,
    ptm_to_choi,
)


PAPER_ID = "projected_ls_qpt_2022"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Projected Least-Squares Quantum Process Tomography",
    "venue": "Quantum",
    "year": 2022,
    "doi": "10.22331/q-2022-10-20-844",
    "role": "physical_qpt_reconstruction",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def shot_noise_config(shots: int) -> MultipassQPTConfig:
    return MultipassQPTConfig(
        shots=int(shots),
        readout_scale=1.0,
        readout_bias_x=0.0,
        readout_bias_y=0.0,
        readout_bias_z=0.0,
        prep_shrink=1.0,
        prep_bias_x=0.0,
        prep_bias_y=0.0,
        prep_bias_z=0.0,
    )


def summarize(values: np.ndarray) -> dict[str, float]:
    data = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "median": float(np.median(data)),
        "p90": float(np.percentile(data, 90)),
    }


def monte_carlo_rows(
    actual_ptm: np.ndarray,
    shots: int,
    seeds: tuple[int, ...],
    projection_iterations: int,
) -> tuple[list[dict[str, float]], list[dict[str, object]]]:
    true_choi = ptm_to_choi(actual_ptm)
    rows: list[dict[str, float]] = []
    representatives: list[dict[str, object]] = []
    config = shot_noise_config(shots)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        raw_ptm = simulate_qpt_estimate(actual_ptm, 1, config, rng)
        result = projected_least_squares_qpt(raw_ptm, iterations=projection_iterations)
        rows.append(
            {
                "seed": int(seed),
                "raw_choi_error": choi_frobenius_error(result.raw_choi, true_choi),
                "psd_choi_error": choi_frobenius_error(result.psd_choi, true_choi),
                "cptp_choi_error": choi_frobenius_error(result.cptp_choi, true_choi),
                "raw_ptm_error": ptm_frobenius_error(result.raw_ptm, actual_ptm),
                "cptp_ptm_error": ptm_frobenius_error(result.cptp_ptm, actual_ptm),
                "raw_min_eigenvalue": result.raw_physicality.min_eigenvalue,
                "cptp_min_eigenvalue": result.cptp_physicality.min_eigenvalue,
                "raw_negative_eigenvalue_sum": result.raw_physicality.negative_eigenvalue_sum,
                "cptp_negative_eigenvalue_sum": result.cptp_physicality.negative_eigenvalue_sum,
                "raw_tp_residual": result.raw_physicality.trace_preserving_residual,
                "cptp_tp_residual": result.cptp_physicality.trace_preserving_residual,
            }
        )
        if len(representatives) < 1:
            representatives.append(
                {
                    "seed": int(seed),
                    "raw_ptm": result.raw_ptm,
                    "cptp_ptm": result.cptp_ptm,
                    "raw_choi_eigenvalues": np.linalg.eigvalsh(result.raw_choi).real,
                    "cptp_choi_eigenvalues": np.linalg.eigvalsh(result.cptp_choi).real,
                }
            )
    return rows, representatives


def shot_sweep_rows(
    actual_ptm: np.ndarray,
    shot_levels: tuple[int, ...],
    seeds: tuple[int, ...],
    projection_iterations: int,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for shots in shot_levels:
        mc_rows, _ = monte_carlo_rows(actual_ptm, shots, seeds, projection_iterations)
        raw_errors = np.array([row["raw_choi_error"] for row in mc_rows], dtype=float)
        cptp_errors = np.array([row["cptp_choi_error"] for row in mc_rows], dtype=float)
        raw_neg = np.array([row["raw_negative_eigenvalue_sum"] for row in mc_rows], dtype=float)
        cptp_neg = np.array([row["cptp_negative_eigenvalue_sum"] for row in mc_rows], dtype=float)
        rows.append(
            {
                "shots": int(shots),
                "raw_choi_error_mean": float(np.mean(raw_errors)),
                "cptp_choi_error_mean": float(np.mean(cptp_errors)),
                "raw_negative_sum_mean": float(np.mean(raw_neg)),
                "cptp_negative_sum_mean": float(np.mean(cptp_neg)),
                "improvement_factor": float(np.mean(raw_errors) / max(np.mean(cptp_errors), 1e-15)),
            }
        )
    return rows


def plot_error_distribution(path: Path, rows: list[dict[str, float]]) -> None:
    raw = np.array([row["raw_choi_error"] for row in rows], dtype=float)
    psd = np.array([row["psd_choi_error"] for row in rows], dtype=float)
    cptp = np.array([row["cptp_choi_error"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.4, 5.0), constrained_layout=True)
    ax.hist(raw, bins=18, alpha=0.55, label="raw LS")
    ax.hist(psd, bins=18, alpha=0.55, label="PSD only")
    ax.hist(cptp, bins=18, alpha=0.55, label="CPTP PLS")
    ax.set_title("QPT Choi reconstruction error under shot noise")
    ax.set_xlabel("Choi Frobenius error")
    ax.set_ylabel("Monte Carlo count")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_eigenvalues(path: Path, representative: dict[str, object]) -> None:
    raw = np.asarray(representative["raw_choi_eigenvalues"], dtype=float)
    cptp = np.asarray(representative["cptp_choi_eigenvalues"], dtype=float)
    x = np.arange(len(raw))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    ax.bar(x - width / 2.0, raw, width=width, label="raw LS")
    ax.bar(x + width / 2.0, cptp, width=width, label="CPTP PLS")
    ax.axhline(0.0, color="0.25", lw=1.0)
    ax.set_title("Representative Choi eigenvalues")
    ax.set_xlabel("eigenvalue index")
    ax.set_ylabel("eigenvalue")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_shot_sweep(path: Path, rows: list[dict[str, float]]) -> None:
    shots = np.array([row["shots"] for row in rows], dtype=float)
    raw = np.array([row["raw_choi_error_mean"] for row in rows], dtype=float)
    cptp = np.array([row["cptp_choi_error_mean"] for row in rows], dtype=float)
    raw_neg = np.array([row["raw_negative_sum_mean"] for row in rows], dtype=float)
    cptp_neg = np.array([row["cptp_negative_sum_mean"] for row in rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), constrained_layout=True)
    axes[0].loglog(shots, raw, marker="o", label="raw LS")
    axes[0].loglog(shots, cptp, marker="s", label="CPTP PLS")
    axes[0].set_title("Mean Choi error vs shots")
    axes[0].set_xlabel("shots")
    axes[0].set_ylabel("mean Choi error")
    axes[0].grid(alpha=0.25, which="both")
    axes[0].legend()
    axes[1].loglog(shots, raw_neg, marker="o", label="raw LS")
    axes[1].loglog(shots, np.maximum(cptp_neg, 1e-16), marker="s", label="CPTP PLS")
    axes[1].set_title("Mean CP violation vs shots")
    axes[1].set_xlabel("shots")
    axes[1].set_ylabel("sum of negative Choi eigenvalues")
    axes[1].grid(alpha=0.25, which="both")
    axes[1].legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_ptm_comparison(
    path: Path,
    actual_ptm: np.ndarray,
    representative: dict[str, object],
) -> None:
    raw = np.asarray(representative["raw_ptm"], dtype=float)
    cptp = np.asarray(representative["cptp_ptm"], dtype=float)
    matrices = [
        ("true PTM", actual_ptm),
        ("raw LS PTM", raw),
        ("CPTP PLS PTM", cptp),
        ("PLS - true", cptp - actual_ptm),
    ]
    vmax = max(float(np.max(np.abs(matrix))) for _, matrix in matrices)
    fig, axes = plt.subplots(1, 4, figsize=(13.0, 3.4), constrained_layout=True)
    for ax, (title, matrix) in zip(axes, matrices):
        image = ax.imshow(matrix, vmin=-vmax, vmax=vmax, cmap="coolwarm")
        ax.set_title(title, fontsize=9)
        ax.set_xticks(range(4), ["I", "X", "Y", "Z"])
        ax.set_yticks(range(4), ["I", "X", "Y", "Z"])
        ax.set_xlabel("input Pauli")
        ax.set_ylabel("output Pauli")
    fig.colorbar(image, ax=axes, shrink=0.8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    _, actual_ptm = single_qubit_process()
    shots = 128
    projection_iterations = 100
    seeds = tuple(range(100, 200))
    rows, representatives = monte_carlo_rows(actual_ptm, shots, seeds, projection_iterations)
    representative = representatives[0]
    shot_rows = shot_sweep_rows(
        actual_ptm,
        shot_levels=(64, 128, 256, 512, 1024, 2048),
        seeds=tuple(range(300, 340)),
        projection_iterations=projection_iterations,
    )

    raw_errors = np.array([row["raw_choi_error"] for row in rows], dtype=float)
    psd_errors = np.array([row["psd_choi_error"] for row in rows], dtype=float)
    cptp_errors = np.array([row["cptp_choi_error"] for row in rows], dtype=float)
    raw_negative = np.array([row["raw_negative_eigenvalue_sum"] for row in rows], dtype=float)
    cptp_negative = np.array([row["cptp_negative_eigenvalue_sum"] for row in rows], dtype=float)

    figures = {
        "qpt_error_distribution": figure_dir / "qpt_error_distribution.png",
        "choi_eigenvalues_raw_vs_pls": figure_dir / "choi_eigenvalues_raw_vs_pls.png",
        "physicality_violations_vs_shots": figure_dir / "physicality_violations_vs_shots.png",
        "ptm_reconstruction_comparison": figure_dir / "ptm_reconstruction_comparison.png",
    }
    plot_error_distribution(figures["qpt_error_distribution"], rows)
    plot_eigenvalues(figures["choi_eigenvalues_raw_vs_pls"], representative)
    plot_shot_sweep(figures["physicality_violations_vs_shots"], shot_rows)
    plot_ptm_comparison(figures["ptm_reconstruction_comparison"], actual_ptm, representative)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "projected_least_squares_qpt",
        "simulation": {
            "process": "single-qubit sqrt-X-like PTM from the multipass QPT benchmark",
            "shots": shots,
            "seed_count": len(seeds),
            "projection_iterations": projection_iterations,
            "noise_model": "shot noise only; no SPAM bias in the primary benchmark",
        },
        "error_summary": {
            "raw_choi_error": summarize(raw_errors),
            "psd_choi_error": summarize(psd_errors),
            "cptp_choi_error": summarize(cptp_errors),
            "mean_error_improvement_raw_to_cptp": float(np.mean(raw_errors) / max(np.mean(cptp_errors), 1e-15)),
        },
        "physicality_summary": {
            "raw_negative_fraction": float(np.mean(raw_negative > 1e-12)),
            "cptp_negative_fraction": float(np.mean(cptp_negative > 1e-12)),
            "raw_negative_eigenvalue_sum": summarize(raw_negative),
            "cptp_negative_eigenvalue_sum": summarize(cptp_negative),
            "raw_tp_residual_mean": float(np.mean([row["raw_tp_residual"] for row in rows])),
            "cptp_tp_residual_mean": float(np.mean([row["cptp_tp_residual"] for row in rows])),
        },
        "shot_sweep": shot_rows,
        "representative_seed": int(representative["seed"]),
        "scientific_interpretation": {
            "captures": [
                "least-squares QPT can produce a non-CP Choi matrix under finite sampling",
                "PSD projection removes negative Choi eigenvalues but does not enforce TP by itself",
                "CPTP projection yields a physically valid process estimate",
                "the benchmark is directly useful before using QPT estimates in hardware or control loops",
            ],
            "does_not_capture": [
                "the full theorem-level finite-sample analysis of the paper is not reproduced",
                "large-dimensional tensor-network or many-qubit scaling is not implemented",
                "SPAM bias is not the primary target here; Paper F already isolates SPAM/readout effects",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "least_squares": "raw PTM estimate from linear inversion QPT",
            "choi_conversion": "J(E) = sum_mn |m><n| tensor E(|m><n|)",
            "cp_constraint": "J >= 0",
            "tp_constraint": "Tr_output J = I",
            "pls_projection": "min ||J - J_LS||_F over J >= 0 and Tr_output J = I",
        },
        "assumptions": [
            "The reproduction uses a single-qubit process so the projection is transparent and fast.",
            "The primary benchmark uses finite-shot noise without SPAM bias.",
            "CPTP projection is implemented by Dykstra alternating projections.",
            "The purpose is physical reconstruction, not proving the statistical rates from the paper.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "raw_choi_error_mean": metrics["error_summary"]["raw_choi_error"]["mean"],
            "cptp_choi_error_mean": metrics["error_summary"]["cptp_choi_error"]["mean"],
            "mean_error_improvement_raw_to_cptp": metrics["error_summary"]["mean_error_improvement_raw_to_cptp"],
            "raw_negative_fraction": metrics["physicality_summary"]["raw_negative_fraction"],
            "cptp_negative_fraction": metrics["physicality_summary"]["cptp_negative_fraction"],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the projected least-squares QPT Paper J target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

