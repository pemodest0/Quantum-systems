from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.relaxation_models import (
    TRANSITION_LABELS,
    QuadrupolarRelaxationParams,
    apparent_initial_decay_rates,
    fit_redfield_effective_to_envelopes,
    phenomenological_transition_envelopes,
    redfield_effective_envelopes,
    redfield_inspired_rates,
    reduced_spectral_densities,
)


PAPER_ID = "na23_relaxometry_2023"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "23Na relaxometry: An overview of theory and applications",
    "venue": "Magnetic Resonance Letters",
    "year": 2023,
    "doi": "10.1016/j.mrl.2023.04.001",
    "source_urls": [
        "https://doi.org/10.1016/j.mrl.2023.04.001",
        "https://www.sciencedirect.com/science/article/pii/S2772516223000232",
        "https://pubmed.ncbi.nlm.nih.gov/40918001/",
    ],
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def scalar(value: np.ndarray | float) -> float:
    return float(np.asarray(value))


def plot_spectral_density_regimes(
    figure_path: Path,
    tau_grid_s: np.ndarray,
    config: NMRConfig,
) -> None:
    densities = reduced_spectral_densities(tau_grid_s, config.nu0)
    omega0 = 2.0 * np.pi * config.nu0

    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.loglog(tau_grid_s, densities.j0_s, label="J0")
    ax.loglog(tau_grid_s, densities.j1_s, label="J1 at omega0")
    ax.loglog(tau_grid_s, densities.j2_s, label="J2 at 2 omega0")
    ax.axvline(1.0 / omega0, color="0.25", ls="--", lw=1.0, label="omega0 tau_c = 1")
    ax.axvline(1.0 / (2.0 * omega0), color="0.45", ls=":", lw=1.0, label="2 omega0 tau_c = 1")
    ax.set_title("Reduced spectral densities for Na-23 quadrupolar relaxation")
    ax.set_xlabel("correlation time tau_c (s)")
    ax.set_ylabel("J_n(tau_c) (s)")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)


def plot_rates_vs_tau(
    figure_path: Path,
    tau_grid_s: np.ndarray,
    params: QuadrupolarRelaxationParams,
) -> None:
    rates = redfield_inspired_rates(tau_grid_s, params)

    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.loglog(tau_grid_s, rates.r1_slow, label="R1 slow")
    ax.loglog(tau_grid_s, rates.r1_fast, label="R1 fast")
    ax.loglog(tau_grid_s, rates.r2_central, label="R2 central")
    ax.loglog(tau_grid_s, rates.r2_satellite, label="R2 satellite")
    ax.set_title("Effective Redfield-inspired rates vs correlation time")
    ax.set_xlabel("correlation time tau_c (s)")
    ax.set_ylabel("rate (s^-1)")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)


def plot_envelope_comparison(
    figure_path: Path,
    time_s: np.ndarray,
    phenomenological: np.ndarray,
    redfield_effective: np.ndarray,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 8.0), sharex=True, constrained_layout=True)
    for idx, label in enumerate(TRANSITION_LABELS):
        axes[idx].plot(
            time_s * 1e3,
            phenomenological[:, idx],
            label="current phenomenological biexponential",
            lw=1.7,
        )
        axes[idx].plot(
            time_s * 1e3,
            redfield_effective[:, idx],
            label="best Redfield-inspired effective fit",
            lw=1.4,
            ls="--",
        )
        axes[idx].set_ylabel(f"{label} envelope")
        axes[idx].grid(alpha=0.25)
    axes[0].set_title("Current envelope model vs Redfield-inspired effective closure")
    axes[-1].set_xlabel("time (ms)")
    axes[0].legend()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)


def plot_residuals(
    figure_path: Path,
    time_s: np.ndarray,
    phenomenological: np.ndarray,
    redfield_effective: np.ndarray,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    for idx, label in enumerate(TRANSITION_LABELS):
        ax.plot(time_s * 1e3, redfield_effective[:, idx] - phenomenological[:, idx], label=label)
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_title("Envelope residuals: effective model minus current model")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("normalized envelope residual")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig()
    time_s = np.linspace(0.0, 0.025, 800)
    tau_grid_s = np.logspace(-12, -4, 160)
    fit_tau_grid_s = np.logspace(-11, -5, 72)
    fit_coupling_grid_hz = np.logspace(2.0, 4.7, 72)

    phenomenological = phenomenological_transition_envelopes(
        time_s,
        decay_params=config.decay_params,
    )
    fit = fit_redfield_effective_to_envelopes(
        time_s=time_s,
        target_envelopes=phenomenological,
        larmor_hz=config.nu0,
        tau_grid_s=fit_tau_grid_s,
        coupling_grid_hz=fit_coupling_grid_hz,
    )
    fitted_params = QuadrupolarRelaxationParams(
        larmor_hz=config.nu0,
        quadrupolar_coupling_hz=fit.quadrupolar_coupling_hz,
    )
    fitted_rates = redfield_inspired_rates(fit.tau_c_s, fitted_params)
    redfield_effective = redfield_effective_envelopes(time_s, fitted_rates)

    figures = {
        "spectral_density_regimes": figure_dir / "spectral_density_regimes.png",
        "rates_vs_tau_c": figure_dir / "rates_vs_tau_c.png",
        "phenomenological_vs_redfield_decay": figure_dir / "phenomenological_vs_redfield_decay.png",
        "envelope_residuals": figure_dir / "envelope_residuals.png",
    }
    plot_spectral_density_regimes(figures["spectral_density_regimes"], tau_grid_s, config)
    plot_rates_vs_tau(figures["rates_vs_tau_c"], tau_grid_s, fitted_params)
    plot_envelope_comparison(
        figures["phenomenological_vs_redfield_decay"],
        time_s,
        phenomenological,
        redfield_effective,
    )
    plot_residuals(figures["envelope_residuals"], time_s, phenomenological, redfield_effective)

    rmse_by_transition = {
        label: float(np.sqrt(np.mean((redfield_effective[:, idx] - phenomenological[:, idx]) ** 2)))
        for idx, label in enumerate(TRANSITION_LABELS)
    }
    max_abs_residual_by_transition = {
        label: float(np.max(np.abs(redfield_effective[:, idx] - phenomenological[:, idx])))
        for idx, label in enumerate(TRANSITION_LABELS)
    }
    phenom_initial_rates = apparent_initial_decay_rates(time_s, phenomenological, fit_until_s=0.003)
    redfield_initial_rates = apparent_initial_decay_rates(time_s, redfield_effective, fit_until_s=0.003)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "comparison_type": "qualitative effective-model reproduction of a review paper",
        "best_fit": {
            "tau_c_s": fit.tau_c_s,
            "quadrupolar_coupling_hz": fit.quadrupolar_coupling_hz,
            "global_envelope_rmse": fit.rmse,
        },
        "selected_redfield_inspired_rates_s^-1": {
            "r1_slow": scalar(fitted_rates.r1_slow),
            "r1_fast": scalar(fitted_rates.r1_fast),
            "r2_central": scalar(fitted_rates.r2_central),
            "r2_satellite": scalar(fitted_rates.r2_satellite),
            "r2_fast": scalar(fitted_rates.r2_fast),
        },
        "phenomenological_initial_rates_s^-1": phenom_initial_rates,
        "redfield_effective_initial_rates_s^-1": redfield_initial_rates,
        "rmse_by_transition": rmse_by_transition,
        "max_abs_residual_by_transition": max_abs_residual_by_transition,
        "regime_markers": {
            "omega0_tau_c_equals_1_s": 1.0 / (2.0 * np.pi * config.nu0),
            "two_omega0_tau_c_equals_1_s": 1.0 / (4.0 * np.pi * config.nu0),
        },
        "scientific_interpretation": {
            "captures": [
                "Na-23 is treated as a spin-3/2 quadrupolar nucleus.",
                "Relaxation is controlled by reduced spectral densities J0, J1, and J2.",
                "The current biexponential envelope can be compared against a Redfield-inspired effective closure.",
            ],
            "does_not_capture": [
                "No sample-specific electric-field-gradient distribution is inferred.",
                "No full Redfield tensor is derived from microscopic bath coordinates.",
                "Satellite asymmetry in the current data is only represented phenomenologically.",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "nmr_reference_config": {
            "i_spin": config.i_spin,
            "larmor_hz": config.nu0,
            "nu_q_hz": config.nu_q,
            "temperature_k": config.temperature_k,
            "transition_labels": list(TRANSITION_LABELS),
            "current_decay_params": config.decay_params.tolist(),
        },
        "implemented_equations": {
            "spectral_density": "J_n(tau_c) = tau_c / (1 + (n omega0 tau_c)^2), n = 0, 1, 2",
            "effective_r1_slow": "R1_slow = C (J1 + 4 J2)",
            "effective_r1_fast": "R1_fast = C (J0 + J1 + 4 J2)",
            "effective_r2_central": "R2_CT = C (3 J0 + 0.5 J1 + J2)",
            "effective_r2_satellite": "R2_SAT = C (3 J0 + 1.5 J1 + J2)",
            "current_biexponential": "D_k(t) = A1 exp(rate1 t) + A2 exp(rate2 t)",
        },
        "assumptions": [
            "Single correlation time tau_c.",
            "Axially symmetric effective quadrupolar coupling by default.",
            "Rates are effective benchmarks for model selection, not tissue-specific parameters.",
            "The review paper is reproduced as a physically grounded modeling target, not as a digitized figure copy.",
        ],
        "grids": {
            "time_s": {
                "min": float(time_s[0]),
                "max": float(time_s[-1]),
                "points": int(time_s.size),
            },
            "tau_grid_s": {
                "min": float(tau_grid_s[0]),
                "max": float(tau_grid_s[-1]),
                "points": int(tau_grid_s.size),
            },
            "fit_tau_grid_s": {
                "min": float(fit_tau_grid_s[0]),
                "max": float(fit_tau_grid_s[-1]),
                "points": int(fit_tau_grid_s.size),
            },
            "fit_coupling_grid_hz": {
                "min": float(fit_coupling_grid_hz[0]),
                "max": float(fit_coupling_grid_hz[-1]),
                "points": int(fit_coupling_grid_hz.size),
            },
        },
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "figures": {name: str(path) for name, path in figures.items()},
        "summary": {
            "best_tau_c_s": fit.tau_c_s,
            "best_quadrupolar_coupling_hz": fit.quadrupolar_coupling_hz,
            "global_envelope_rmse": fit.rmse,
        },
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce Paper A Na-23 relaxometry model target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

