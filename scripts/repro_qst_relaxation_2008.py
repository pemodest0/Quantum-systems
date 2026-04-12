from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.qst_relaxation import (
    QSTRelaxationRates,
    coherence_order_norms,
    coherent_superposition_state,
    estimate_rates_from_qst,
    mix_with_identity,
    population_biased_state,
    population_deviation_norms,
    reconstruct_qst_trajectory,
    synthetic_relaxation_trajectory,
)


PAPER_ID = "qst_relaxation_2008"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "A study of the relaxation dynamics in a quadrupolar NMR system using Quantum State Tomography",
    "venue": "Journal of Magnetic Resonance",
    "year": 2008,
    "doi": "10.1016/j.jmr.2008.01.009",
    "role": "tomography_and_identification",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def finite_mean(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(np.mean(arr)) if arr.size else float("nan")


def finite_std(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(np.std(arr, ddof=0)) if arr.size else float("nan")


def relative_error(value: float, target: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return float(abs(value - target) / max(abs(target), 1e-15))


def build_initial_states(config: NMRConfig) -> dict[str, np.ndarray]:
    return {
        "population": mix_with_identity(population_biased_state(config.dim), mixing=0.04),
        "coherence": mix_with_identity(coherent_superposition_state(config.dim), mixing=0.04),
    }


def reconstruct_pair(
    config: NMRConfig,
    times_s: np.ndarray,
    rates: QSTRelaxationRates,
    noise_std: float,
    random_seed: int,
    phase_error_rad: float = 0.0,
) -> tuple[object, object, object]:
    initial = build_initial_states(config)
    population_true = synthetic_relaxation_trajectory(
        initial["population"],
        times_s,
        config,
        rates,
        include_unitary_phase=True,
    )
    coherence_true = synthetic_relaxation_trajectory(
        initial["coherence"],
        times_s,
        config,
        rates,
        include_unitary_phase=True,
    )
    population_traj = reconstruct_qst_trajectory(
        "population",
        population_true,
        times_s,
        config,
        noise_std=noise_std,
        phase_error_rad=phase_error_rad,
        random_seed=random_seed,
    )
    coherence_traj = reconstruct_qst_trajectory(
        "coherence",
        coherence_true,
        times_s,
        config,
        noise_std=noise_std,
        phase_error_rad=phase_error_rad,
        random_seed=random_seed + 10_000,
    )
    estimate = estimate_rates_from_qst(population_traj, coherence_traj, config.m_vals)
    return population_traj, coherence_traj, estimate


def plot_density_element_decay(
    path: Path,
    config: NMRConfig,
    population_traj: object,
    coherence_traj: object,
) -> None:
    time_ms = population_traj.times_s * 1e3
    pop_true = population_deviation_norms(population_traj.true_states)
    pop_rec = population_deviation_norms(population_traj.reconstructed_states)
    true_orders = coherence_order_norms(coherence_traj.true_states, config.m_vals)
    rec_orders = coherence_order_norms(coherence_traj.reconstructed_states, config.m_vals)

    fig, axes = plt.subplots(2, 1, figsize=(9.0, 7.5), sharex=True, constrained_layout=True)
    axes[0].semilogy(time_ms, pop_true, label="true population deviation", lw=1.8)
    axes[0].semilogy(time_ms, pop_rec, "o", ms=4, label="QST reconstructed", alpha=0.8)
    axes[0].set_ylabel("population deviation norm")
    axes[0].set_title("Synthetic QST relaxation: population and coherence decays")
    axes[0].grid(alpha=0.25, which="both")
    axes[0].legend()

    for order in sorted(true_orders):
        axes[1].semilogy(time_ms, true_orders[order], lw=1.6, label=f"true |q|={order}")
        axes[1].semilogy(time_ms, rec_orders[order], "o", ms=3, alpha=0.75, label=f"QST |q|={order}")
    axes[1].set_xlabel("time (ms)")
    axes[1].set_ylabel("coherence-order norm")
    axes[1].grid(alpha=0.25, which="both")
    axes[1].legend(ncols=3, fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_noise_stress(
    config: NMRConfig,
    times_s: np.ndarray,
    rates: QSTRelaxationRates,
    noise_levels: tuple[float, ...],
    seeds: tuple[int, ...],
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for noise_std in noise_levels:
        for seed in seeds:
            try:
                pop_traj, coh_traj, estimate = reconstruct_pair(
                    config,
                    times_s,
                    rates,
                    noise_std=float(noise_std),
                    random_seed=int(seed),
                )
                mean_fidelity = float(np.mean(np.concatenate([pop_traj.fidelities, coh_traj.fidelities])))
                min_fidelity = float(np.min(np.concatenate([pop_traj.fidelities, coh_traj.fidelities])))
                gamma_pop = float(estimate.gamma_population)
                gamma_phi = float(estimate.gamma_dephasing)
            except Exception:
                mean_fidelity = float("nan")
                min_fidelity = float("nan")
                gamma_pop = float("nan")
                gamma_phi = float("nan")

            rows.append(
                {
                    "noise_std": float(noise_std),
                    "seed": int(seed),
                    "mean_fidelity": mean_fidelity,
                    "min_fidelity": min_fidelity,
                    "gamma_population": gamma_pop,
                    "gamma_dephasing": gamma_phi,
                    "relative_error_gamma_population": relative_error(gamma_pop, rates.gamma_population),
                    "relative_error_gamma_dephasing": relative_error(gamma_phi, rates.gamma_dephasing),
                }
            )
    return rows


def summarize_noise(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    noise_levels = sorted({row["noise_std"] for row in rows})
    summary: list[dict[str, float]] = []
    for noise_std in noise_levels:
        subset = [row for row in rows if row["noise_std"] == noise_std]
        summary.append(
            {
                "noise_std": noise_std,
                "mean_fidelity": finite_mean([row["mean_fidelity"] for row in subset]),
                "std_fidelity": finite_std([row["mean_fidelity"] for row in subset]),
                "mean_gamma_population": finite_mean([row["gamma_population"] for row in subset]),
                "std_gamma_population": finite_std([row["gamma_population"] for row in subset]),
                "mean_gamma_dephasing": finite_mean([row["gamma_dephasing"] for row in subset]),
                "std_gamma_dephasing": finite_std([row["gamma_dephasing"] for row in subset]),
                "mean_rel_error_gamma_population": finite_mean(
                    [row["relative_error_gamma_population"] for row in subset]
                ),
                "mean_rel_error_gamma_dephasing": finite_mean(
                    [row["relative_error_gamma_dephasing"] for row in subset]
                ),
            }
        )
    return summary


def plot_fidelity_vs_noise(path: Path, summary: list[dict[str, float]]) -> None:
    noise = np.array([row["noise_std"] for row in summary], dtype=float)
    fidelity = np.array([row["mean_fidelity"] for row in summary], dtype=float)
    std = np.array([row["std_fidelity"] for row in summary], dtype=float)

    fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    ax.errorbar(noise * 100.0, fidelity, yerr=std, marker="o", capsize=4, lw=1.5)
    ax.set_title("QST reconstruction fidelity vs synthetic complex signal noise")
    ax.set_xlabel("tomography signal noise (% of max signal)")
    ax.set_ylabel("mean state fidelity")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_rate_recovery(path: Path, summary: list[dict[str, float]], rates: QSTRelaxationRates) -> None:
    noise = np.array([row["noise_std"] for row in summary], dtype=float) * 100.0
    pop = np.array([row["mean_gamma_population"] for row in summary], dtype=float)
    pop_std = np.array([row["std_gamma_population"] for row in summary], dtype=float)
    phi = np.array([row["mean_gamma_dephasing"] for row in summary], dtype=float)
    phi_std = np.array([row["std_gamma_dephasing"] for row in summary], dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7.0), sharex=True, constrained_layout=True)
    axes[0].errorbar(noise, pop, yerr=pop_std, marker="o", capsize=4, label="QST estimate")
    axes[0].axhline(rates.gamma_population, color="0.2", ls="--", label="true")
    axes[0].set_ylabel("gamma_population (s^-1)")
    axes[0].set_title("Rate extraction from reconstructed density matrices")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].errorbar(noise, phi, yerr=phi_std, marker="o", capsize=4, label="QST estimate")
    axes[1].axhline(rates.gamma_dephasing, color="0.2", ls="--", label="true")
    axes[1].set_xlabel("tomography signal noise (% of max signal)")
    axes[1].set_ylabel("gamma_dephasing (s^-1)")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_phase_sensitivity(
    config: NMRConfig,
    times_s: np.ndarray,
    rates: QSTRelaxationRates,
    phase_errors_deg: tuple[float, ...],
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for phase_deg in phase_errors_deg:
        phase_rad = np.deg2rad(float(phase_deg))
        try:
            pop_traj, coh_traj, estimate = reconstruct_pair(
                config,
                times_s,
                rates,
                noise_std=0.0,
                phase_error_rad=phase_rad,
                random_seed=4242,
            )
            mean_fidelity = float(np.mean(np.concatenate([pop_traj.fidelities, coh_traj.fidelities])))
            gamma_pop = float(estimate.gamma_population)
            gamma_phi = float(estimate.gamma_dephasing)
        except Exception:
            mean_fidelity = float("nan")
            gamma_pop = float("nan")
            gamma_phi = float("nan")
        rows.append(
            {
                "phase_error_deg": float(phase_deg),
                "mean_fidelity": mean_fidelity,
                "gamma_population": gamma_pop,
                "gamma_dephasing": gamma_phi,
                "relative_error_gamma_population": relative_error(gamma_pop, rates.gamma_population),
                "relative_error_gamma_dephasing": relative_error(gamma_phi, rates.gamma_dephasing),
            }
        )
    return rows


def plot_phase_sensitivity(path: Path, rows: list[dict[str, float]]) -> None:
    phase = np.array([row["phase_error_deg"] for row in rows], dtype=float)
    fidelity = np.array([row["mean_fidelity"] for row in rows], dtype=float)
    pop_err = np.array([row["relative_error_gamma_population"] for row in rows], dtype=float)
    phi_err = np.array([row["relative_error_gamma_dephasing"] for row in rows], dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.6), sharex=True, constrained_layout=True)
    axes[0].plot(phase, fidelity, marker="o", lw=1.4)
    axes[0].set_ylabel("mean fidelity")
    axes[0].set_title("Tomography phase-error sensitivity")
    axes[0].grid(alpha=0.25)

    axes[1].plot(phase, pop_err, marker="o", lw=1.4, label="gamma_population")
    axes[1].plot(phase, phi_err, marker="s", lw=1.4, label="gamma_dephasing")
    axes[1].set_xlabel("phase ramp error per tomography step (deg)")
    axes[1].set_ylabel("relative rate error")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig(n_acq=256, n_zf=256)
    true_rates = QSTRelaxationRates(gamma_population=52.0, gamma_dephasing=24.0)
    times_s = np.linspace(0.0, 0.012, 18)

    population_traj, coherence_traj, noiseless_estimate = reconstruct_pair(
        config,
        times_s,
        true_rates,
        noise_std=0.0,
        random_seed=1001,
    )
    noise_rows = run_noise_stress(
        config,
        times_s,
        true_rates,
        noise_levels=(0.0, 0.002, 0.01, 0.03),
        seeds=(11, 23, 37),
    )
    noise_summary = summarize_noise(noise_rows)
    phase_rows = run_phase_sensitivity(
        config,
        times_s,
        true_rates,
        phase_errors_deg=(0.0, 0.5, 1.0, 2.0, 4.0),
    )

    figures = {
        "density_element_decay": figure_dir / "density_element_decay.png",
        "tomography_fidelity_vs_noise": figure_dir / "tomography_fidelity_vs_noise.png",
        "extracted_rate_vs_true": figure_dir / "extracted_rate_vs_true.png",
        "phase_error_sensitivity": figure_dir / "phase_error_sensitivity.png",
    }
    plot_density_element_decay(figures["density_element_decay"], config, population_traj, coherence_traj)
    plot_fidelity_vs_noise(figures["tomography_fidelity_vs_noise"], noise_summary)
    plot_rate_recovery(figures["extracted_rate_vs_true"], noise_summary, true_rates)
    plot_phase_sensitivity(figures["phase_error_sensitivity"], phase_rows)

    noiseless_mean_fidelity = float(
        np.mean(np.concatenate([population_traj.fidelities, coherence_traj.fidelities]))
    )
    noiseless_min_fidelity = float(
        np.min(np.concatenate([population_traj.fidelities, coherence_traj.fidelities]))
    )

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "true_rates_s^-1": {
            "gamma_population": true_rates.gamma_population,
            "gamma_dephasing": true_rates.gamma_dephasing,
        },
        "noiseless_reconstruction": {
            "mean_fidelity": noiseless_mean_fidelity,
            "min_fidelity": noiseless_min_fidelity,
            "max_frobenius_error": float(
                np.max(np.concatenate([population_traj.frobenius_errors, coherence_traj.frobenius_errors]))
            ),
            "gamma_population_estimate": noiseless_estimate.gamma_population,
            "gamma_dephasing_estimate": noiseless_estimate.gamma_dephasing,
            "relative_error_gamma_population": relative_error(
                noiseless_estimate.gamma_population,
                true_rates.gamma_population,
            ),
            "relative_error_gamma_dephasing": relative_error(
                noiseless_estimate.gamma_dephasing,
                true_rates.gamma_dephasing,
            ),
            "coherence_order_rates": {
                str(order): value for order, value in noiseless_estimate.coherence_order_rates.items()
            },
            "population_fit_rmse": noiseless_estimate.population_fit_rmse,
            "coherence_fit_rmse": noiseless_estimate.coherence_fit_rmse,
        },
        "noise_stress_cases": noise_rows,
        "noise_summary": noise_summary,
        "phase_error_sensitivity": phase_rows,
        "scientific_interpretation": {
            "captures": [
                "density-matrix elements are reconstructed at each relaxation time",
                "population and coherence decay rates are estimated from reconstructed states",
                "noise and tomography phase errors are propagated into rate-estimation error",
            ],
            "does_not_capture": [
                "no full experimental pulse calibration is used",
                "no real QST phase-series raw data are available yet",
                "the synthetic relaxation channel is an effective Redfield-like benchmark, not a full microscopic Redfield tensor",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "nmr_reference_config": {
            "i_spin": config.i_spin,
            "dim": config.dim,
            "larmor_hz": config.nu0,
            "nu_q_hz": config.nu_q,
            "t_tomo_s": config.t_tomo,
            "tomography_phases": 7,
            "transition_labels": list(config.transition_labels),
        },
        "implemented_equations": {
            "synthetic_channel": "rho(t) = dephase_q[ exp(-gamma_pop t) rho0 + (1-exp(-gamma_pop t)) I/d ]",
            "coherence_decay": "|rho_ij(t)| ~ exp[-(gamma_pop + gamma_phi q^2)t], q = m_i - m_j",
            "tomography": "A vec(rho) = b solved by least squares with trace constraint",
            "rate_fit": "log norm(t) = intercept - rate t",
        },
        "assumptions": [
            "Two synthetic initial states are used: population-biased and coherent-superposition.",
            "Initial states are slightly mixed to avoid singular fidelity artifacts.",
            "The reproduction uses synthetic QST data because no time-resolved experimental QST dataset is present yet.",
            "The paper result is reproduced as a workflow: QST time series -> density-matrix elements -> fitted relaxation rates.",
        ],
        "time_grid_s": {
            "min": float(times_s[0]),
            "max": float(times_s[-1]),
            "points": int(times_s.size),
        },
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": {
            "noiseless_mean_fidelity": noiseless_mean_fidelity,
            "noiseless_gamma_population_estimate": noiseless_estimate.gamma_population,
            "noiseless_gamma_dephasing_estimate": noiseless_estimate.gamma_dephasing,
            "relative_error_gamma_population": metrics["noiseless_reconstruction"][
                "relative_error_gamma_population"
            ],
            "relative_error_gamma_dephasing": metrics["noiseless_reconstruction"][
                "relative_error_gamma_dephasing"
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# QST Relaxation Dynamics In A Quadrupolar NMR System",
                "",
                "This run reproduces the workflow logic of the 2008 QST relaxation paper",
                "with synthetic data: generate relaxation trajectories, reconstruct density",
                "matrices by QST, estimate rates, and stress test noise/phase errors.",
                "",
                f"Noiseless mean fidelity: `{noiseless_mean_fidelity:.8f}`.",
                f"True gamma_population: `{true_rates.gamma_population:.6g} s^-1`.",
                f"Estimated gamma_population: `{noiseless_estimate.gamma_population:.6g} s^-1`.",
                f"True gamma_dephasing: `{true_rates.gamma_dephasing:.6g} s^-1`.",
                f"Estimated gamma_dephasing: `{noiseless_estimate.gamma_dephasing:.6g} s^-1`.",
                "",
                "This is not yet an experimental reproduction because no time-resolved",
                "QST phase-series raw data are present in the repository.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the QST relaxation Paper C target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
