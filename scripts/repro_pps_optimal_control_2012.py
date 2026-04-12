from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.grape_control import (
    dephase_in_measurement_basis,
    deviation_preparation_error,
    deviation_transfer_efficiency,
    optimize_state_preparation_grape,
    prepare_state_with_dephasing,
    propagate_controls,
    random_controls,
    target_pseudo_pure_from_deviation,
    thermal_deviation_state_from_iz,
)
from oqs_control.platforms.na23_nmr.qst_relaxation import add_tomography_noise
from oqs_control.platforms.na23_nmr.quadrupolar_qip import COMPUTATIONAL_BASIS, deviation_fidelity
from oqs_control.platforms.na23_nmr.tomography import (
    reconstruct_density_matrix,
    simulate_tomography_signals,
    state_fidelity,
)


PAPER_ID = "pps_optimal_control_2012"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Preparing Pseudo-Pure States in a Quadrupolar Spin System Using Optimal Control",
    "venue": "Chinese Physics Letters",
    "year": 2012,
    "doi": "10.1088/0256-307X/29/12/127601",
    "role": "state_preparation_bridge",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def givens_rotation(dim: int, i: int, j: int, cos_squared: float) -> np.ndarray:
    c = float(np.sqrt(cos_squared))
    s = float(np.sqrt(1.0 - cos_squared))
    unitary = np.eye(dim, dtype=complex)
    unitary[i, i] = c
    unitary[j, j] = c
    unitary[i, j] = s
    unitary[j, i] = -s
    return unitary


def analytical_population_averaging_unitary(dim: int = 4) -> np.ndarray:
    """Return the ideal population-mixing unitary for the |00> PPS target."""

    return (
        givens_rotation(dim, 2, 3, 0.5)
        @ givens_rotation(dim, 1, 3, 0.4)
        @ givens_rotation(dim, 0, 3, 0.75)
    )


def coherence_norm(rho: np.ndarray) -> float:
    matrix = np.asarray(rho, dtype=complex)
    off_diag = matrix - np.diag(np.diag(matrix))
    return float(np.linalg.norm(off_diag))


def qst_noise_rows(
    config: NMRConfig,
    target_state: np.ndarray,
    prepared_state: np.ndarray,
    noise_levels: tuple[float, ...],
    seeds: tuple[int, ...],
) -> list[dict[str, float]]:
    clean_signals = simulate_tomography_signals(prepared_state, config)
    rows: list[dict[str, float]] = []
    for noise_std in noise_levels:
        state_fids: list[float] = []
        dev_fids: list[float] = []
        prep_errors: list[float] = []
        for seed in seeds:
            rng = np.random.default_rng(seed)
            measured = add_tomography_noise(clean_signals, noise_std, rng)
            qst = reconstruct_density_matrix(measured, config, rho_true=prepared_state)
            reconstructed = qst.reconstructed_rho
            state_fids.append(state_fidelity(prepared_state, reconstructed))
            dev_fids.append(deviation_fidelity(target_state, reconstructed))
            prep_errors.append(deviation_preparation_error(reconstructed, target_state))
        rows.append(
            {
                "noise_std": float(noise_std),
                "prepared_state_fidelity_mean": float(np.mean(state_fids)),
                "prepared_state_fidelity_std": float(np.std(state_fids)),
                "target_deviation_fidelity_mean": float(np.mean(dev_fids)),
                "target_deviation_fidelity_std": float(np.std(dev_fids)),
                "target_preparation_error_mean": float(np.mean(prep_errors)),
            }
        )
    return rows


def plot_population_profiles(
    path: Path,
    rho_initial: np.ndarray,
    target_state: np.ndarray,
    analytical_state: np.ndarray,
    grape_state: np.ndarray,
) -> None:
    labels = list(COMPUTATIONAL_BASIS)
    values = [
        ("thermal input", np.real(np.diag(rho_initial))),
        ("target PPS", np.real(np.diag(target_state))),
        ("ideal mixing", np.real(np.diag(analytical_state))),
        ("GRAPE + gradient", np.real(np.diag(grape_state))),
    ]
    x = np.arange(len(labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(8.8, 5.1), constrained_layout=True)
    for idx, (name, diag) in enumerate(values):
        ax.bar(x + (idx - 1.5) * width, diag, width=width, label=name)
    ax.set_title("Pseudo-pure-state population preparation")
    ax.set_ylabel("population")
    ax.set_xticks(x, labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_convergence(path: Path, history: tuple[float, ...]) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.plot(np.arange(1, len(history) + 1), history, lw=1.8)
    ax.set_title("PPS GRAPE preparation-score convergence")
    ax.set_xlabel("objective evaluation")
    ax.set_ylabel("1 - normalized deviation error")
    ax.set_ylim(min(-0.1, min(history) - 0.05), 1.02)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_controls(path: Path, controls: np.ndarray, dt_s: float) -> None:
    time_us = (np.arange(controls.shape[0]) + 0.5) * dt_s * 1e6
    ux_hz = controls[:, 0] / (2.0 * np.pi)
    uy_hz = controls[:, 1] / (2.0 * np.pi)
    amp_hz = np.linalg.norm(controls, axis=1) / (2.0 * np.pi)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), constrained_layout=True)
    ax.step(time_us, ux_hz, where="mid", label="u_x")
    ax.step(time_us, uy_hz, where="mid", label="u_y")
    ax.step(time_us, amp_hz, where="mid", color="0.25", ls="--", label="amplitude")
    ax.set_title("Optimized RF controls for PPS preparation")
    ax.set_xlabel("time (us)")
    ax.set_ylabel("control amplitude (Hz)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_qst_noise(path: Path, rows: list[dict[str, float]]) -> None:
    x = np.array([row["noise_std"] for row in rows], dtype=float)
    prepared = np.array([row["prepared_state_fidelity_mean"] for row in rows], dtype=float)
    prepared_std = np.array([row["prepared_state_fidelity_std"] for row in rows], dtype=float)
    target_dev = np.array([row["target_deviation_fidelity_mean"] for row in rows], dtype=float)
    target_dev_std = np.array([row["target_deviation_fidelity_std"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.errorbar(x, prepared, yerr=prepared_std, marker="o", capsize=3, label="QST vs prepared state")
    ax.errorbar(x, target_dev, yerr=target_dev_std, marker="s", capsize=3, label="QST vs PPS target")
    ax.set_title("QST sensitivity for optimized PPS preparation")
    ax.set_xlabel("relative complex tomography noise")
    ax.set_ylabel("fidelity")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig(n_acq=256, n_zf=256)
    marked_index = 0
    thermal_scale = 0.03
    rho_initial = thermal_deviation_state_from_iz(config.i_z, scale=thermal_scale)
    target_state = target_pseudo_pure_from_deviation(marked_index, rho_initial)

    analytical_u = analytical_population_averaging_unitary(config.dim)
    analytical_state = dephase_in_measurement_basis(
        analytical_u @ rho_initial @ analytical_u.conj().T
    )

    duration_s = 900e-6
    n_segments = 14
    dt_s = duration_s / n_segments
    max_amplitude_rad_s = 2.0 * np.pi * 16e3
    controls0 = random_controls(n_segments, max_amplitude_rad_s, seed=22, scale=0.4)
    result = optimize_state_preparation_grape(
        rho_initial,
        target_state,
        controls0,
        dt_s,
        config.h_free,
        config.i_x,
        config.i_y,
        max_amplitude_rad_s=max_amplitude_rad_s,
        max_iter=45,
    )
    unitary_only = propagate_controls(
        result.controls,
        dt_s,
        config.h_free,
        config.i_x,
        config.i_y,
    )
    before_gradient = unitary_only @ rho_initial @ unitary_only.conj().T
    prepared_state = prepare_state_with_dephasing(
        result.controls,
        dt_s,
        config.h_free,
        config.i_x,
        config.i_y,
        rho_initial,
    )

    qst_rows = qst_noise_rows(
        config,
        target_state,
        prepared_state,
        noise_levels=(0.0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.08),
        seeds=tuple(range(900, 930)),
    )

    figures = {
        "pps_population_profiles": figure_dir / "pps_population_profiles.png",
        "pps_grape_convergence": figure_dir / "pps_grape_convergence.png",
        "pps_optimized_controls": figure_dir / "pps_optimized_controls.png",
        "pps_qst_noise_sensitivity": figure_dir / "pps_qst_noise_sensitivity.png",
    }
    plot_population_profiles(figures["pps_population_profiles"], rho_initial, target_state, analytical_state, prepared_state)
    plot_convergence(figures["pps_grape_convergence"], result.fidelity_history)
    plot_controls(figures["pps_optimized_controls"], result.controls, dt_s)
    plot_qst_noise(figures["pps_qst_noise_sensitivity"], qst_rows)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "pps_optimal_control",
        "target_state": {
            "marked_label": COMPUTATIONAL_BASIS[marked_index],
            "marked_index": marked_index,
            "thermal_scale": thermal_scale,
            "initial_populations": [float(value) for value in np.real(np.diag(rho_initial))],
            "target_populations": [float(value) for value in np.real(np.diag(target_state))],
        },
        "analytical_population_averaging": {
            "populations": [float(value) for value in np.real(np.diag(analytical_state))],
            "deviation_fidelity": deviation_fidelity(analytical_state, target_state),
            "preparation_error": deviation_preparation_error(analytical_state, target_state),
            "signal_efficiency": deviation_transfer_efficiency(analytical_state, target_state),
        },
        "grape_preparation": {
            "duration_s": duration_s,
            "n_segments": n_segments,
            "dt_s": dt_s,
            "max_amplitude_hz": max_amplitude_rad_s / (2.0 * np.pi),
            "initial_deviation_fidelity": result.initial_deviation_fidelity,
            "final_deviation_fidelity": result.final_deviation_fidelity,
            "initial_signal_efficiency": result.initial_signal_efficiency,
            "final_signal_efficiency": result.final_signal_efficiency,
            "initial_preparation_error": 1.0 - result.fidelity_history[0],
            "final_preparation_error": deviation_preparation_error(prepared_state, target_state),
            "coherence_norm_before_gradient": coherence_norm(before_gradient),
            "coherence_norm_after_gradient": coherence_norm(prepared_state),
            "iterations": result.iterations,
            "success": result.success,
            "optimizer_message": result.message,
            "prepared_populations": [float(value) for value in np.real(np.diag(prepared_state))],
        },
        "qst_noise_sensitivity": qst_rows,
        "scientific_interpretation": {
            "captures": [
                "pseudo-pure-state preparation is treated as a density-matrix target, not only a unitary gate",
                "the identity component is retained but the deviation density is the NMR-relevant object",
                "a dephasing/gradient step removes coherences after optimized RF mixing",
                "synthetic QST checks whether the prepared PPS can be reconstructed under measurement noise",
            ],
            "does_not_capture": [
                "no shaped-pulse calibration from a real spectrometer is used",
                "no relaxation during the PPS pulse is included",
                "the optimized objective is a minimal density-matrix benchmark rather than the full experimental protocol",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "thermal_input": "rho = I/4 + scale Iz",
            "pps_target": "rho_pps = I/4 + scale (0.75 |00><00| - 0.25 sum_other |j><j|)",
            "control_then_gradient": "rho_out = dephase[U(u) rho_in U(u)^dagger]",
            "preparation_error": "||dev(rho_out)-dev(rho_target)|| / ||dev(rho_target)||",
            "qst": "signals from seven tomography rotations, then A vec(rho)=b",
        },
        "assumptions": [
            "The benchmark prepares the |00> pseudo-pure state in the four-level spin-3/2 manifold.",
            "The gradient pulse is represented as perfect dephasing in the measurement basis.",
            "The target signal scale follows the population-averaging PPS amplitude reachable from thermal Iz.",
            "Tomography noise is synthetic and relative to simulated complex tomography amplitudes.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "analytical_preparation_error": metrics["analytical_population_averaging"]["preparation_error"],
            "grape_final_preparation_error": metrics["grape_preparation"]["final_preparation_error"],
            "grape_final_deviation_fidelity": result.final_deviation_fidelity,
            "grape_final_signal_efficiency": result.final_signal_efficiency,
            "qst_noise_0p02_target_deviation_fidelity_mean": next(
                row["target_deviation_fidelity_mean"]
                for row in qst_rows
                if abs(row["noise_std"] - 0.02) < 1e-15
            ),
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the PPS optimal-control Paper I target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

