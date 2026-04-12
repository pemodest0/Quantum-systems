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
    average_output_bloch_fidelity,
    estimate_single_process_from_multipass,
    ptm_frobenius_error,
    run_multipass_monte_carlo,
    simulate_qpt_estimate,
    single_qubit_process,
)


PAPER_ID = "multipass_qpt_2024"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Multipass quantum process tomography",
    "venue": "Scientific Reports",
    "year": 2024,
    "doi": "10.1038/s41598-024-68353-3",
    "published": "2024-08-06",
    "role": "future_hardware_characterization",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def summarize_errors(errors: np.ndarray) -> dict[str, float]:
    values = np.asarray(errors, dtype=float)
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=0)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
    }


def plot_error_vs_passes(
    path: Path,
    passes: tuple[int, ...],
    single_errors: np.ndarray,
    multipass_errors: dict[int, np.ndarray],
) -> None:
    x = np.array([1, *passes], dtype=float)
    means = [float(np.mean(single_errors))]
    stds = [float(np.std(single_errors))]
    for passes_n in passes:
        means.append(float(np.mean(multipass_errors[passes_n])))
        stds.append(float(np.std(multipass_errors[passes_n])))

    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.errorbar(x, means, yerr=stds, marker="o", capsize=4, lw=1.5)
    ax.set_title("Single-pass QPT vs multipass QPT root extraction")
    ax.set_xlabel("number of process passes N")
    ax.set_ylabel("PTM Frobenius error to true single process")
    ax.set_xticks(x)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_error_distributions(
    path: Path,
    single_errors: np.ndarray,
    multipass_errors: dict[int, np.ndarray],
    best_passes: int,
) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.hist(single_errors, bins=16, alpha=0.65, label="single-pass SQPT")
    ax.hist(multipass_errors[best_passes], bins=16, alpha=0.65, label=f"multipass N={best_passes}")
    ax.set_title("Error distribution under SPAM/readout/shot noise")
    ax.set_xlabel("PTM Frobenius error")
    ax.set_ylabel("Monte Carlo count")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_ptm_comparison(
    path: Path,
    true_ptm: np.ndarray,
    single_est: np.ndarray,
    multipass_est: np.ndarray,
    best_passes: int,
) -> None:
    matrices = [
        ("true process PTM", true_ptm),
        ("single-pass estimate", single_est),
        (f"multipass N={best_passes} estimate", multipass_est),
        ("multipass - true", multipass_est - true_ptm),
    ]
    vmax = max(float(np.max(np.abs(matrix))) for _, matrix in matrices)
    fig, axes = plt.subplots(1, 4, figsize=(13.0, 3.4), constrained_layout=True)
    for ax, (title, matrix) in zip(axes, matrices):
        image = ax.imshow(matrix, vmin=-vmax, vmax=vmax, cmap="coolwarm")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("input Pauli")
        ax.set_ylabel("output Pauli")
        ax.set_xticks(range(4), ["I", "X", "Y", "Z"])
        ax.set_yticks(range(4), ["I", "X", "Y", "Z"])
    fig.colorbar(image, ax=axes, shrink=0.8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def shot_sweep(
    passes: int,
    shot_levels: tuple[int, ...],
    seeds: tuple[int, ...],
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for shots in shot_levels:
        _, _, result = run_multipass_monte_carlo(
            passes=(passes,),
            shots=shots,
            seeds=seeds,
        )
        rows.append(
            {
                "shots": int(shots),
                "single_mean_error": float(np.mean(result.single_errors)),
                "single_std_error": float(np.std(result.single_errors)),
                "multipass_mean_error": float(np.mean(result.multipass_errors[passes])),
                "multipass_std_error": float(np.std(result.multipass_errors[passes])),
                "improvement_factor": float(result.improvement_factors[passes]),
            }
        )
    return rows


def plot_shot_sweep(path: Path, rows: list[dict[str, float]], passes: int) -> None:
    shots = np.array([row["shots"] for row in rows], dtype=float)
    single = np.array([row["single_mean_error"] for row in rows], dtype=float)
    single_std = np.array([row["single_std_error"] for row in rows], dtype=float)
    multi = np.array([row["multipass_mean_error"] for row in rows], dtype=float)
    multi_std = np.array([row["multipass_std_error"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.loglog(shots, single, marker="o", label="single-pass SQPT")
    ax.fill_between(shots, np.maximum(single - single_std, 1e-12), single + single_std, alpha=0.18)
    ax.loglog(shots, multi, marker="s", label=f"multipass N={passes}")
    ax.fill_between(shots, np.maximum(multi - multi_std, 1e-12), multi + multi_std, alpha=0.18)
    ax.set_title("Shot-noise sensitivity")
    ax.set_xlabel("shots per measurement")
    ax.set_ylabel("PTM Frobenius error")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    target_ptm, actual_ptm = single_qubit_process()
    passes = (2, 3, 5, 7)
    seeds = tuple(range(100, 160))
    shots = 512
    _, _, mc = run_multipass_monte_carlo(passes=passes, shots=shots, seeds=seeds)
    best_passes = max(mc.improvement_factors, key=mc.improvement_factors.get)

    rng = np.random.default_rng(2024)
    qpt_config = MultipassQPTConfig(shots=shots)
    single_est = simulate_qpt_estimate(actual_ptm, 1, qpt_config, rng)
    measured_power = simulate_qpt_estimate(actual_ptm, best_passes, qpt_config, rng)
    multipass_est = estimate_single_process_from_multipass(measured_power, target_ptm, best_passes)

    shot_rows = shot_sweep(
        passes=best_passes,
        shot_levels=(128, 256, 512, 1024, 2048, 4096),
        seeds=tuple(range(200, 230)),
    )

    figures = {
        "error_vs_passes": figure_dir / "error_vs_passes.png",
        "single_vs_multipass_error_distribution": figure_dir / "single_vs_multipass_error_distribution.png",
        "ptm_comparison": figure_dir / "ptm_comparison.png",
        "shot_noise_sweep": figure_dir / "shot_noise_sweep.png",
    }
    plot_error_vs_passes(figures["error_vs_passes"], passes, mc.single_errors, mc.multipass_errors)
    plot_error_distributions(
        figures["single_vs_multipass_error_distribution"],
        mc.single_errors,
        mc.multipass_errors,
        best_passes,
    )
    plot_ptm_comparison(figures["ptm_comparison"], actual_ptm, single_est, multipass_est, best_passes)
    plot_shot_sweep(figures["shot_noise_sweep"], shot_rows, best_passes)

    multipass_summary = {
        str(passes_n): {
            "error": summarize_errors(mc.multipass_errors[passes_n]),
            "improvement_factor": mc.improvement_factors[passes_n],
        }
        for passes_n in passes
    }
    single_summary = summarize_errors(mc.single_errors)
    best_summary = multipass_summary[str(best_passes)]

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "process": {
            "target": "sqrt-X-like rotation",
            "actual_error_model": "coherent X overrotation plus isotropic depolarizing shrink",
            "ptm_frobenius_error_target_to_actual": ptm_frobenius_error(actual_ptm, target_ptm),
        },
        "monte_carlo": {
            "shots": shots,
            "seed_count": len(seeds),
            "passes": list(passes),
            "single_pass_error": single_summary,
            "multipass": multipass_summary,
            "best_passes": int(best_passes),
            "best_improvement_factor": float(mc.improvement_factors[best_passes]),
        },
        "representative_estimates": {
            "single_pass_error": ptm_frobenius_error(single_est, actual_ptm),
            "multipass_error": ptm_frobenius_error(multipass_est, actual_ptm),
            "single_pass_average_probe_fidelity": average_output_bloch_fidelity(single_est, actual_ptm),
            "multipass_average_probe_fidelity": average_output_bloch_fidelity(multipass_est, actual_ptm),
            "best_passes": int(best_passes),
        },
        "shot_sweep": shot_rows,
        "transferability_note": {
            "useful_for_hardware": [
                "gate repetitions amplify coherent process errors while SPAM/readout errors remain at circuit boundaries",
                "post-processing can estimate the single-process PTM from the measured multipass PTM",
                "the method is compatible with qubit hardware characterization workflows",
            ],
            "limits_for_na23_nmr": [
                "Na-23 spin-3/2 NMR is a four-level system, not a physical qubit unless an encoded subspace is selected",
                "selective-pulse leakage and quadrupolar evolution during pulses must be modeled before applying MQPT directly",
                "process repetitions must be experimentally repeatable with stable phase and RF calibration",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "ptm_definition": "R_ij = Tr(P_i E(P_j)) / 2",
            "standard_qpt": "R_est = S_out S_in^{-1}",
            "multipass_process": "R_N = R^N",
            "target_error_frame": "E_N = R_N T_N^{-1}",
            "single_process_recovery": "R_est = E_N^(1/N) T",
        },
        "simulation_config": {
            "shots": shots,
            "passes": list(passes),
            "seeds": list(seeds),
            "qpt_config": {
                "readout_scale": qpt_config.readout_scale,
                "readout_bias_x": qpt_config.readout_bias_x,
                "readout_bias_y": qpt_config.readout_bias_y,
                "readout_bias_z": qpt_config.readout_bias_z,
                "prep_shrink": qpt_config.prep_shrink,
                "prep_bias_x": qpt_config.prep_bias_x,
                "prep_bias_y": qpt_config.prep_bias_y,
                "prep_bias_z": qpt_config.prep_bias_z,
            },
        },
        "assumptions": [
            "The reproduced prototype is single-qubit PTM QPT.",
            "The target is sqrt-X-like because the paper demonstrates MQPT on sqrt-X.",
            "The root extraction is performed in the target error frame to avoid branch ambiguity.",
            "The default error model is chosen to commute with the target frame, matching the small-error MQPT assumption.",
            "This is a synthetic hardware-characterization prototype, not a run on a real IBM backend.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "best_passes": int(best_passes),
            "single_pass_mean_error": single_summary["mean"],
            "best_multipass_mean_error": best_summary["error"]["mean"],
            "best_improvement_factor": float(mc.improvement_factors[best_passes]),
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the multipass QPT Paper F target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

