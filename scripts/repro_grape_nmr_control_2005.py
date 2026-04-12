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
    ControlEnsembleMember,
    optimize_unitary_grape,
    propagate_controls,
    random_controls,
    rectangular_controls,
    unitary_fidelity,
)
from oqs_control.platforms.na23_nmr.selective_pulses import (
    ideal_selective_rotation,
    probe_states,
    selected_transition_frame_hamiltonian,
)


PAPER_ID = "grape_nmr_control_2005"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Optimal control of coupled spin dynamics: Design of NMR pulse sequences by gradient ascent algorithms",
    "venue": "Journal of Magnetic Resonance",
    "year": 2005,
    "doi": "10.1016/j.jmr.2004.11.004",
    "role": "optimal_control_bridge",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensemble_members(
    config: NMRConfig,
    base_drift: np.ndarray,
    detunings_hz: tuple[float, ...],
    rf_scales: tuple[float, ...],
) -> tuple[ControlEnsembleMember, ...]:
    return tuple(
        ControlEnsembleMember(
            drift=base_drift + 2.0 * np.pi * detuning_hz * config.i_z,
            rf_scale=rf_scale,
            weight=1.0,
        )
        for detuning_hz in detunings_hz
        for rf_scale in rf_scales
    )


def fidelity_grid(
    config: NMRConfig,
    controls: np.ndarray,
    dt_s: float,
    target: np.ndarray,
    base_drift: np.ndarray,
    detunings_hz: np.ndarray,
    rf_scales: np.ndarray,
) -> np.ndarray:
    grid = np.zeros((len(rf_scales), len(detunings_hz)), dtype=float)
    for row, rf_scale in enumerate(rf_scales):
        for col, detuning_hz in enumerate(detunings_hz):
            drift = base_drift + 2.0 * np.pi * float(detuning_hz) * config.i_z
            unitary = propagate_controls(
                controls,
                dt_s,
                drift,
                config.i_x,
                config.i_y,
                rf_scale=float(rf_scale),
            )
            grid[row, col] = unitary_fidelity(target, unitary)
    return grid


def summarize_grid(grid: np.ndarray) -> dict[str, float]:
    values = np.asarray(grid, dtype=float)
    return {
        "min": float(np.min(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "max": float(np.max(values)),
        "p10": float(np.percentile(values, 10)),
    }


def plot_convergence(path: Path, history: tuple[float, ...], rectangular_mean: float) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.plot(np.arange(1, len(history) + 1), history, lw=1.8, label="GRAPE optimization")
    ax.axhline(rectangular_mean, color="0.35", ls="--", lw=1.2, label="rectangular mean")
    ax.set_title("GRAPE unitary fidelity convergence")
    ax.set_xlabel("objective evaluation")
    ax.set_ylabel("ensemble-averaged unitary fidelity")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_controls(path: Path, controls: np.ndarray, dt_s: float) -> None:
    time_us = (np.arange(controls.shape[0]) + 0.5) * dt_s * 1e6
    ux_hz = controls[:, 0] / (2.0 * np.pi)
    uy_hz = controls[:, 1] / (2.0 * np.pi)
    amp_hz = np.linalg.norm(controls, axis=1) / (2.0 * np.pi)
    phase = np.unwrap(np.arctan2(controls[:, 1], controls[:, 0]))

    fig, axes = plt.subplots(2, 1, figsize=(8.6, 6.2), constrained_layout=True)
    axes[0].step(time_us, ux_hz, where="mid", label="u_x")
    axes[0].step(time_us, uy_hz, where="mid", label="u_y")
    axes[0].step(time_us, amp_hz, where="mid", color="0.25", ls="--", label="amplitude")
    axes[0].set_title("Optimized piecewise-constant RF controls")
    axes[0].set_ylabel("control amplitude (Hz)")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].step(time_us, phase, where="mid", color="tab:orange")
    axes[1].set_xlabel("time (us)")
    axes[1].set_ylabel("unwrapped phase (rad)")
    axes[1].grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_robustness_maps(
    path: Path,
    rect_grid: np.ndarray,
    opt_grid: np.ndarray,
    detunings_hz: np.ndarray,
    rf_scales: np.ndarray,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1), constrained_layout=True)
    payload = [
        ("rectangular pulse", rect_grid),
        ("GRAPE pulse", opt_grid),
        ("GRAPE - rectangular", opt_grid - rect_grid),
    ]
    for ax, (title, grid) in zip(axes, payload):
        if " - " in title:
            image = ax.imshow(
                grid,
                origin="lower",
                aspect="auto",
                extent=[detunings_hz[0], detunings_hz[-1], rf_scales[0], rf_scales[-1]],
                vmin=-1.0,
                vmax=1.0,
                cmap="coolwarm",
            )
        else:
            image = ax.imshow(
                grid,
                origin="lower",
                aspect="auto",
                extent=[detunings_hz[0], detunings_hz[-1], rf_scales[0], rf_scales[-1]],
                vmin=0.0,
                vmax=1.0,
                cmap="viridis",
            )
        ax.set_title(title)
        ax.set_xlabel("B0 detuning (Hz)")
        ax.set_ylabel("B1 scale")
        fig.colorbar(image, ax=ax, shrink=0.85)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def probe_state_rows(
    target: np.ndarray,
    rect_unitary: np.ndarray,
    opt_unitary: np.ndarray,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    labels = ["basis_0", "basis_1", "basis_2", "basis_3", "coherent", "balanced_ct"]
    for label, rho in zip(labels, probe_states(4)):
        target_state = target @ rho @ target.conj().T
        rect_state = rect_unitary @ rho @ rect_unitary.conj().T
        opt_state = opt_unitary @ rho @ opt_unitary.conj().T
        rows.append(
            {
                "state": label,
                "rectangular_fidelity": float(np.clip(np.real(np.trace(target_state @ rect_state)), 0.0, 1.0)),
                "grape_fidelity": float(np.clip(np.real(np.trace(target_state @ opt_state)), 0.0, 1.0)),
            }
        )
    return rows


def plot_probe_state_fidelities(path: Path, rows: list[dict[str, float | str]]) -> None:
    labels = [str(row["state"]) for row in rows]
    rect = np.array([float(row["rectangular_fidelity"]) for row in rows], dtype=float)
    grape = np.array([float(row["grape_fidelity"]) for row in rows], dtype=float)
    x = np.arange(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8.8, 5.0), constrained_layout=True)
    ax.bar(x - width / 2.0, rect, width=width, label="rectangular")
    ax.bar(x + width / 2.0, grape, width=width, label="GRAPE")
    ax.set_title("State-level validation of the optimized selective gate")
    ax.set_ylabel("state fidelity")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylim(0.0, 1.02)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig(n_acq=256, n_zf=256)
    transition_index = 1
    pair = config.transition_pairs[transition_index]
    target = ideal_selective_rotation(config.dim, pair, np.pi)
    base_drift = selected_transition_frame_hamiltonian(config, pair)

    duration_s = 500e-6
    n_segments = 24
    dt_s = duration_s / n_segments
    max_amplitude_rad_s = 2.0 * np.pi * 14e3
    rectangular = rectangular_controls(n_segments, duration_s, np.pi)
    initial_controls = 0.65 * rectangular + 0.35 * random_controls(
        n_segments,
        max_amplitude_rad_s,
        seed=123,
        scale=0.16,
    )
    training_detunings_hz = (-200.0, 0.0, 200.0)
    training_rf_scales = (0.95, 1.0, 1.05)
    training_ensemble = ensemble_members(
        config,
        base_drift,
        training_detunings_hz,
        training_rf_scales,
    )

    result = optimize_unitary_grape(
        target,
        initial_controls,
        dt_s,
        training_ensemble,
        config.i_x,
        config.i_y,
        max_amplitude_rad_s=max_amplitude_rad_s,
        max_iter=70,
    )

    grid_detunings_hz = np.linspace(-500.0, 500.0, 41)
    grid_rf_scales = np.linspace(0.85, 1.15, 31)
    rect_grid = fidelity_grid(
        config,
        rectangular,
        dt_s,
        target,
        base_drift,
        grid_detunings_hz,
        grid_rf_scales,
    )
    opt_grid = fidelity_grid(
        config,
        result.controls,
        dt_s,
        target,
        base_drift,
        grid_detunings_hz,
        grid_rf_scales,
    )

    rect_unitary = propagate_controls(rectangular, dt_s, base_drift, config.i_x, config.i_y)
    opt_unitary = propagate_controls(result.controls, dt_s, base_drift, config.i_x, config.i_y)
    state_rows = probe_state_rows(target, rect_unitary, opt_unitary)

    rect_summary = summarize_grid(rect_grid)
    opt_summary = summarize_grid(opt_grid)
    figures = {
        "grape_fidelity_convergence": figure_dir / "grape_fidelity_convergence.png",
        "optimized_controls": figure_dir / "optimized_controls.png",
        "robustness_map": figure_dir / "robustness_map.png",
        "rectangular_vs_grape_state_fidelity": figure_dir / "rectangular_vs_grape_state_fidelity.png",
    }
    plot_convergence(figures["grape_fidelity_convergence"], result.fidelity_history, rect_summary["mean"])
    plot_controls(figures["optimized_controls"], result.controls, dt_s)
    plot_robustness_maps(
        figures["robustness_map"],
        rect_grid,
        opt_grid,
        grid_detunings_hz,
        grid_rf_scales,
    )
    plot_probe_state_fidelities(figures["rectangular_vs_grape_state_fidelity"], state_rows)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "grape_unitary_control",
        "target_operation": {
            "platform": "Na-23 spin-3/2 encoded manifold",
            "transition": config.transition_labels[transition_index],
            "transition_pair": list(pair),
            "operation": "selective pi rotation on the central transition",
        },
        "optimization": {
            "duration_s": duration_s,
            "n_segments": n_segments,
            "dt_s": dt_s,
            "max_amplitude_hz": max_amplitude_rad_s / (2.0 * np.pi),
            "training_detunings_hz": list(training_detunings_hz),
            "training_rf_scales": list(training_rf_scales),
            "initial_training_mean_fidelity": result.initial_fidelity,
            "final_training_mean_fidelity": result.final_fidelity,
            "iterations": result.iterations,
            "success": result.success,
            "optimizer_message": result.message,
        },
        "robustness_grid": {
            "detuning_hz_min": float(grid_detunings_hz[0]),
            "detuning_hz_max": float(grid_detunings_hz[-1]),
            "rf_scale_min": float(grid_rf_scales[0]),
            "rf_scale_max": float(grid_rf_scales[-1]),
            "rectangular": rect_summary,
            "grape": opt_summary,
            "mean_improvement": float(opt_summary["mean"] - rect_summary["mean"]),
            "min_improvement": float(opt_summary["min"] - rect_summary["min"]),
        },
        "probe_state_fidelities": state_rows,
        "scientific_interpretation": {
            "captures": [
                "piecewise-constant RF controls are optimized by gradient ascent",
                "the objective is a unitary gate fidelity averaged over B0 detuning and B1 scale",
                "the optimized pulse suppresses leakage and coherent phase errors relative to a rectangular pulse",
                "the benchmark directly addresses the selective-pulse failure mode observed in Paper D",
            ],
            "does_not_capture": [
                "no relaxation-optimized Liouville-space GRAPE is implemented here",
                "no experimental RF transfer function or amplifier bandwidth is modeled",
                "the benchmark targets one spin-3/2 selective operation rather than a coupled multi-spin molecule",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "piecewise_constant_unitary": "U = product_k exp[-i (H0 + ux_k Hx + uy_k Hy) dt]",
            "unitary_fidelity": "F = |Tr(U_target^dagger U)|^2 / d^2",
            "ensemble_objective": "Phi = mean_{B0,B1} F(B0, B1)",
            "grape_gradient": "dF/du_k from Frechet derivative of exp[-i H_k dt]",
        },
        "assumptions": [
            "The reproduction implements the core GRAPE algorithmic idea, not a digitized figure.",
            "The target system is the current Na-23 spin-3/2 model, not the original paper's coupled-spin examples.",
            "Controls are global RF fields along Ix and Iy in the selected central-transition frame.",
            "Robustness is trained over a small synthetic B0/B1 ensemble.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "initial_training_mean_fidelity": result.initial_fidelity,
            "final_training_mean_fidelity": result.final_fidelity,
            "rectangular_grid_mean_fidelity": rect_summary["mean"],
            "grape_grid_mean_fidelity": opt_summary["mean"],
            "rectangular_grid_min_fidelity": rect_summary["min"],
            "grape_grid_min_fidelity": opt_summary["min"],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the GRAPE NMR-control Paper H target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

