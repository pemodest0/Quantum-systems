from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .platforms.na23_nmr import NMRConfig
from .platforms.na23_nmr.analysis import fft_spectrum, flatten_first_trace, summarize_reference
from .platforms.na23_nmr.config_io import save_config_json as save_nmr_config_json
from .platforms.na23_nmr.experimental_tomography import (
    ExtractionSettings,
    load_phase_manifest,
    reconstruct_from_manifest,
    reconstruct_from_simulated_phase_series,
)
from .platforms.na23_nmr.dissipative_fitting import (
    fit_reference_dissipative_rates,
    run_synthetic_dissipative_recovery,
    run_synthetic_validation_suite,
)
from .platforms.na23_nmr.fitting import fit_reference_spectrum
from .platforms.na23_nmr.io import read_tnt
from .platforms.na23_nmr.liouvillian import NMRDissipationRates, simulate_open_reference_experiment
from .platforms.na23_nmr.simulation import simulate_reference_experiment
from .platforms.na23_nmr.tomography import reconstruct_density_matrix, simulate_tomography_signals
from .workflows import run_open_qubit_demo


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_outputs_dir() -> Path:
    outputs = project_root() / "outputs"
    outputs.mkdir(exist_ok=True)
    return outputs


def default_reference_path() -> Path:
    return project_root() / "data" / "reference" / "Referential2.tnt"


def _heatmap(ax: plt.Axes, mat: np.ndarray, title: str) -> None:
    image = ax.imshow(mat, cmap="coolwarm")
    ax.set_title(title)
    ax.set_xlabel("column")
    ax.set_ylabel("row")
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)


def _normalize_abs(signal: np.ndarray) -> np.ndarray:
    magnitude = np.abs(signal)
    scale = np.max(magnitude)
    if scale == 0:
        return magnitude
    return magnitude / scale


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oqs-control",
        description="Open quantum systems control and dissipative dynamics research workspace.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    open_demo = sub.add_parser("open-system-demo", help="Run the classical open-qubit demo.")
    open_demo.add_argument("--figure", type=Path, default=default_outputs_dir() / "open_qubit_demo.png")
    open_demo.add_argument("--json", type=Path, default=default_outputs_dir() / "open_qubit_demo.json")

    nmr_an = sub.add_parser("nmr-analyze-reference", help="Analyze the NMR reference TNT file.")
    nmr_an.add_argument("--reference", type=Path, default=default_reference_path())

    nmr_fit = sub.add_parser("nmr-fit-reference", help="Fit the NMR reference spectrum.")
    nmr_fit.add_argument("--reference", type=Path, default=default_reference_path())
    nmr_fit.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_reference_fit.png")
    nmr_fit.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_reference_fit.json")

    nmr_sim = sub.add_parser("nmr-simulate-reference", help="Simulate and compare the NMR reference dataset.")
    nmr_sim.add_argument("--reference", type=Path, default=default_reference_path())
    nmr_sim.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_reference_vs_simulation.png")

    nmr_open = sub.add_parser("nmr-open-simulate", help="Run an explicit Liouvillian Na-23 NMR simulation.")
    nmr_open.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_open_simulation.png")
    nmr_open.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_open_simulation.json")
    nmr_open.add_argument("--n-points", type=int, default=768)
    nmr_open.add_argument("--gamma-phi", type=float, default=160.0)
    nmr_open.add_argument("--gamma-relax", type=float, default=35.0)

    nmr_syn_fit = sub.add_parser(
        "nmr-synthetic-dissipation-fit",
        help="Recover effective dissipative rates from synthetic Na-23 FID data.",
    )
    nmr_syn_fit.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_synthetic_dissipation_fit.png")
    nmr_syn_fit.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_synthetic_dissipation_fit.json")
    nmr_syn_fit.add_argument("--n-points", type=int, default=384)
    nmr_syn_fit.add_argument("--true-gamma-phi", type=float, default=210.0)
    nmr_syn_fit.add_argument("--true-gamma-relax", type=float, default=55.0)
    nmr_syn_fit.add_argument("--initial-gamma-phi", type=float, default=90.0)
    nmr_syn_fit.add_argument("--initial-gamma-relax", type=float, default=18.0)
    nmr_syn_fit.add_argument("--noise-std", type=float, default=0.0)
    nmr_syn_fit.add_argument("--random-seed", type=int, default=1234)

    nmr_val = sub.add_parser(
        "nmr-validation-suite",
        help="Run synthetic robustness validation for the Na-23 dissipative fitting workflow.",
    )
    nmr_val.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_validation_suite.png")
    nmr_val.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_validation_suite.json")
    nmr_val.add_argument("--n-points", type=int, default=128)
    nmr_val.add_argument("--noise-levels", type=float, nargs="+", default=[0.0, 0.002, 0.01])
    nmr_val.add_argument("--seeds", type=int, nargs="+", default=[11, 23, 37])
    nmr_val.add_argument("--true-gamma-phi", type=float, default=210.0)
    nmr_val.add_argument("--true-gamma-relax", type=float, default=55.0)
    nmr_val.add_argument("--initial-gamma-phi", type=float, default=90.0)
    nmr_val.add_argument("--initial-gamma-relax", type=float, default=18.0)

    nmr_real_diss = sub.add_parser(
        "nmr-fit-reference-dissipation",
        help="Run a diagnostic effective-dissipation fit on the reference TNT FID.",
    )
    nmr_real_diss.add_argument("--reference", type=Path, default=default_reference_path())
    nmr_real_diss.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_reference_dissipation_fit.png")
    nmr_real_diss.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_reference_dissipation_fit.json")
    nmr_real_diss.add_argument("--n-points", type=int, default=512)
    nmr_real_diss.add_argument("--initial-gamma-phi", type=float, default=160.0)
    nmr_real_diss.add_argument("--initial-gamma-relax", type=float, default=35.0)

    nmr_td = sub.add_parser("nmr-tomography-demo", help="Run direct tomography on synthetic NMR signals.")
    nmr_td.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_tomography_demo.png")
    nmr_td.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_tomography_demo.json")

    nmr_tp = sub.add_parser(
        "nmr-tomography-pipeline-demo",
        help="Run end-to-end NMR tomography from synthetic FIDs and spectral extraction.",
    )
    nmr_tp.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_tomography_pipeline.png")
    nmr_tp.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_tomography_pipeline.json")
    nmr_tp.add_argument("--line-broadening-hz", type=float, default=20.0)
    nmr_tp.add_argument("--integration-window-hz", type=float, default=1000.0)
    nmr_tp.add_argument("--diagnostic-search-hz", type=float, default=1800.0)
    nmr_tp.add_argument("--zero-fill-factor", type=int, default=4)

    nmr_exp = sub.add_parser(
        "nmr-experimental-tomography",
        help="Run NMR tomography from a 7-phase TNT manifest.",
    )
    nmr_exp.add_argument(
        "--manifest",
        type=Path,
        default=project_root() / "examples" / "experimental_tomography_manifest.template.json",
    )
    nmr_exp.add_argument("--figure", type=Path, default=default_outputs_dir() / "nmr_experimental_tomography.png")
    nmr_exp.add_argument("--json", type=Path, default=default_outputs_dir() / "nmr_experimental_tomography.json")
    nmr_exp.add_argument("--line-broadening-hz", type=float, default=20.0)
    nmr_exp.add_argument("--integration-window-hz", type=float, default=1000.0)
    nmr_exp.add_argument("--diagnostic-search-hz", type=float, default=1800.0)
    nmr_exp.add_argument("--zero-fill-factor", type=int, default=4)

    cfg = sub.add_parser("export-research-config", help="Export the current NMR platform configuration.")
    cfg.add_argument("--output", type=Path, default=project_root() / "examples" / "nmr_default_config.generated.json")

    return parser


def cmd_open_system_demo(figure: Path, json_path: Path) -> int:
    result = run_open_qubit_demo()
    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), constrained_layout=True)
    axes[0, 0].plot(result.times, result.sigma_x_expectation.real, lw=1.6)
    axes[0, 0].set_title("<sigma_x>")
    axes[0, 0].grid(alpha=0.25)
    axes[0, 1].plot(result.times, result.sigma_z_expectation.real, lw=1.6)
    axes[0, 1].set_title("<sigma_z>")
    axes[0, 1].grid(alpha=0.25)
    axes[1, 0].plot(result.times, result.purity, lw=1.6, label="purity")
    axes[1, 0].plot(result.times, result.entropy, lw=1.4, label="entropy")
    axes[1, 0].set_title("State metrics")
    axes[1, 0].grid(alpha=0.25)
    axes[1, 0].legend()
    axes[1, 1].plot(result.times, result.entropy_production, lw=1.4, label="entropy production proxy")
    axes[1, 1].plot(result.times, result.free_energy_like, lw=1.4, label="free-energy-like")
    axes[1, 1].set_title("Statistical-physics observables")
    axes[1, 1].grid(alpha=0.25)
    axes[1, 1].legend()
    for ax in axes.flat:
        ax.set_xlabel("time")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "final_purity": float(result.purity[-1]),
        "final_entropy": float(result.entropy[-1]),
        "final_entropy_production": float(result.entropy_production[-1]),
        "final_free_energy_like": float(result.free_energy_like[-1]),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_analyze_reference(reference: Path) -> int:
    print(json.dumps(summarize_reference(reference), indent=2, ensure_ascii=False))
    return 0


def cmd_nmr_fit_reference(reference: Path, figure: Path, json_path: Path) -> int:
    fit = fit_reference_spectrum(reference)
    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.plot(fit.freq_hz, fit.reference_magnitude, lw=1.8, label="experiment")
    ax.plot(fit.freq_hz, fit.fitted_magnitude, lw=1.4, label="fit")
    ax.set_title("Reference spectrum fit")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("normalized |FFT|")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "success": fit.success,
        "message": fit.message,
        "cost": fit.cost,
        "nfev": fit.nfev,
        "nu_q_hz": fit.nu_q_hz,
        "t_pi2_us": fit.t_pi2_us,
        "line_broadening_hz": fit.line_broadening_hz,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_simulate_reference(reference: Path, figure: Path) -> int:
    config = NMRConfig()
    sim = simulate_reference_experiment(config)
    ref = read_tnt(reference)
    ref_fid = flatten_first_trace(ref)
    ref_freq_hz, ref_spec = fft_spectrum(ref_fid, dwell_time=config.dwell_time)
    sim_norm = np.abs(sim.spectrum) / np.max(np.abs(sim.spectrum))
    ref_norm = np.abs(ref_spec) / np.max(np.abs(ref_spec))

    figure.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
    axes[0].plot(sim.time_s * 1e3, sim.fid.real, lw=1.3, label="sim real")
    axes[0].plot(sim.time_s * 1e3, sim.fid.imag, lw=1.0, label="sim imag", alpha=0.8)
    axes[0].set_title("Simulated FID")
    axes[0].set_xlabel("time (ms)")
    axes[0].set_ylabel("amplitude")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(ref_freq_hz, ref_norm, lw=1.8, label="experiment")
    axes[1].plot(sim.freq_hz, sim_norm, lw=1.3, label="simulation")
    axes[1].set_title("Reference vs simulation")
    axes[1].set_xlabel("frequency (Hz)")
    axes[1].set_ylabel("normalized |FFT|")
    axes[1].set_xlim(-30000, 30000)
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)
    print(f"Figure saved to: {figure}")
    return 0


def cmd_nmr_open_simulate(
    figure: Path,
    json_path: Path,
    n_points: int,
    gamma_phi: float,
    gamma_relax: float,
) -> int:
    config = NMRConfig(n_acq=n_points, n_zf=n_points)
    rates = NMRDissipationRates(gamma_phi=gamma_phi, gamma_relax=gamma_relax)
    result = simulate_open_reference_experiment(config, rates=rates, n_points=n_points)

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6), constrained_layout=True)
    axes[0, 0].plot(result.time_s * 1e3, result.fid.real, lw=1.3, label="real")
    axes[0, 0].plot(result.time_s * 1e3, result.fid.imag, lw=1.1, label="imag", alpha=0.8)
    axes[0, 0].set_title("Open-system FID")
    axes[0, 0].set_xlabel("time (ms)")
    axes[0, 0].grid(alpha=0.25)
    axes[0, 0].legend()
    axes[0, 1].plot(result.freq_hz, _normalize_abs(result.spectrum), lw=1.4)
    axes[0, 1].set_title("Open-system spectrum")
    axes[0, 1].set_xlabel("frequency (Hz)")
    axes[0, 1].set_xlim(-30000, 30000)
    axes[0, 1].grid(alpha=0.25)
    axes[1, 0].plot(result.time_s * 1e3, result.purity, lw=1.4, label="purity")
    axes[1, 0].plot(result.time_s * 1e3, result.entropy, lw=1.2, label="entropy")
    axes[1, 0].set_title("State metrics")
    axes[1, 0].set_xlabel("time (ms)")
    axes[1, 0].grid(alpha=0.25)
    axes[1, 0].legend()
    axes[1, 1].plot(result.time_s * 1e3, result.relative_entropy_to_mixed, lw=1.3, label="relative entropy")
    axes[1, 1].plot(result.time_s * 1e3, result.entropy_production_proxy, lw=1.1, label="entropy production proxy")
    axes[1, 1].set_title("Open-system diagnostics")
    axes[1, 1].set_xlabel("time (ms)")
    axes[1, 1].grid(alpha=0.25)
    axes[1, 1].legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "rates": {
            "gamma_phi_s^-1": result.rates.gamma_phi,
            "gamma_relax_s^-1": result.rates.gamma_relax,
        },
        "checks": {
            "max_trace_error": result.checks.max_trace_error,
            "max_hermiticity_error": result.checks.max_hermiticity_error,
            "min_eigenvalue": result.checks.min_eigenvalue,
        },
        "final_metrics": {
            "purity": float(result.purity[-1]),
            "entropy": float(result.entropy[-1]),
            "relative_entropy_to_mixed": float(result.relative_entropy_to_mixed[-1]),
            "entropy_production_proxy": float(result.entropy_production_proxy[-1]),
            "free_energy_like": float(result.free_energy_like[-1]),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_synthetic_dissipation_fit(
    figure: Path,
    json_path: Path,
    n_points: int,
    true_gamma_phi: float,
    true_gamma_relax: float,
    initial_gamma_phi: float,
    initial_gamma_relax: float,
    noise_std: float,
    random_seed: int,
) -> int:
    config = NMRConfig(n_acq=n_points, n_zf=n_points)
    result = run_synthetic_dissipative_recovery(
        config=config,
        true_rates=NMRDissipationRates(gamma_phi=true_gamma_phi, gamma_relax=true_gamma_relax),
        initial_rates=NMRDissipationRates(gamma_phi=initial_gamma_phi, gamma_relax=initial_gamma_relax),
        n_points=n_points,
        noise_std=noise_std,
        random_seed=random_seed,
    )

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.2), constrained_layout=True)
    axes[0].plot(result.target.time_s * 1e3, _normalize_abs(result.target.fid), lw=1.7, label="synthetic target")
    axes[0].plot(result.fitted.time_s * 1e3, _normalize_abs(result.fitted.fid), lw=1.2, label="fitted model")
    axes[0].set_title("Synthetic FID recovery")
    axes[0].set_xlabel("time (ms)")
    axes[0].set_ylabel("normalized |FID|")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(result.target.freq_hz, _normalize_abs(result.target.spectrum), lw=1.7, label="synthetic target")
    axes[1].plot(result.fitted.freq_hz, _normalize_abs(result.fitted.spectrum), lw=1.2, label="fitted model")
    axes[1].set_title("Synthetic spectrum recovery")
    axes[1].set_xlabel("frequency (Hz)")
    axes[1].set_ylabel("normalized |FFT|")
    axes[1].set_xlim(-30000, 30000)
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "success": result.success,
        "message": result.message,
        "cost": result.cost,
        "nfev": result.nfev,
        "true_rates": {
            "gamma_phi_s^-1": result.true_rates.gamma_phi,
            "gamma_relax_s^-1": result.true_rates.gamma_relax,
        },
        "initial_rates": {
            "gamma_phi_s^-1": result.initial_rates.gamma_phi,
            "gamma_relax_s^-1": result.initial_rates.gamma_relax,
        },
        "fitted_rates": {
            "gamma_phi_s^-1": result.fitted_rates.gamma_phi,
            "gamma_relax_s^-1": result.fitted_rates.gamma_relax,
        },
        "relative_errors": {
            "gamma_phi": result.relative_error_gamma_phi,
            "gamma_relax": result.relative_error_gamma_relax,
        },
        "physical_checks": {
            "target_max_trace_error": result.target.checks.max_trace_error,
            "target_max_hermiticity_error": result.target.checks.max_hermiticity_error,
            "target_min_eigenvalue": result.target.checks.min_eigenvalue,
            "fitted_max_trace_error": result.fitted.checks.max_trace_error,
            "fitted_max_hermiticity_error": result.fitted.checks.max_hermiticity_error,
            "fitted_min_eigenvalue": result.fitted.checks.min_eigenvalue,
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_validation_suite(
    figure: Path,
    json_path: Path,
    n_points: int,
    noise_levels: list[float],
    seeds: list[int],
    true_gamma_phi: float,
    true_gamma_relax: float,
    initial_gamma_phi: float,
    initial_gamma_relax: float,
) -> int:
    config = NMRConfig(n_acq=n_points, n_zf=n_points)
    suite = run_synthetic_validation_suite(
        config=config,
        true_rates=NMRDissipationRates(gamma_phi=true_gamma_phi, gamma_relax=true_gamma_relax),
        initial_rates=NMRDissipationRates(gamma_phi=initial_gamma_phi, gamma_relax=initial_gamma_relax),
        n_points=n_points,
        noise_levels=tuple(noise_levels),
        random_seeds=tuple(seeds),
    )

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    noise = np.array([case.noise_std for case in suite.cases], dtype=float)
    phi_err = np.array([case.relative_error_gamma_phi for case in suite.cases], dtype=float)
    relax_err = np.array([case.relative_error_gamma_relax for case in suite.cases], dtype=float)
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    ax.scatter(noise, phi_err, label="gamma_phi error", s=42)
    ax.scatter(noise, relax_err, label="gamma_relax error", s=42)
    ax.set_yscale("log")
    ax.set_xlabel("complex noise std / max |FID|")
    ax.set_ylabel("relative error")
    ax.set_title("Synthetic dissipative-rate recovery robustness")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "success_count": suite.success_count,
        "total_count": suite.total_count,
        "true_rates": {
            "gamma_phi_s^-1": suite.true_rates.gamma_phi,
            "gamma_relax_s^-1": suite.true_rates.gamma_relax,
        },
        "initial_rates": {
            "gamma_phi_s^-1": suite.initial_rates.gamma_phi,
            "gamma_relax_s^-1": suite.initial_rates.gamma_relax,
        },
        "summary": {
            "max_relative_error_gamma_phi": suite.max_relative_error_gamma_phi,
            "max_relative_error_gamma_relax": suite.max_relative_error_gamma_relax,
            "median_relative_error_gamma_phi": suite.median_relative_error_gamma_phi,
            "median_relative_error_gamma_relax": suite.median_relative_error_gamma_relax,
        },
        "cases": [
            {
                "noise_std": case.noise_std,
                "random_seed": case.random_seed,
                "success": case.success,
                "cost": case.cost,
                "nfev": case.nfev,
                "fitted_gamma_phi_s^-1": case.fitted_rates.gamma_phi,
                "fitted_gamma_relax_s^-1": case.fitted_rates.gamma_relax,
                "relative_error_gamma_phi": case.relative_error_gamma_phi,
                "relative_error_gamma_relax": case.relative_error_gamma_relax,
            }
            for case in suite.cases
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_fit_reference_dissipation(
    reference: Path,
    figure: Path,
    json_path: Path,
    n_points: int,
    initial_gamma_phi: float,
    initial_gamma_relax: float,
) -> int:
    result = fit_reference_dissipative_rates(
        reference,
        initial_rates=NMRDissipationRates(
            gamma_phi=initial_gamma_phi,
            gamma_relax=initial_gamma_relax,
        ),
        n_points=n_points,
    )

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    scaled_fid = result.complex_scale * (result.fitted.fid / np.max(np.abs(result.fitted.fid)))
    scaled_spec = np.fft.fftshift(np.fft.fft(scaled_fid))
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.2), constrained_layout=True)
    axes[0].plot(np.abs(result.reference_fid), lw=1.5, label="reference |FID|")
    axes[0].plot(np.abs(scaled_fid), lw=1.2, label="diagnostic fit |FID|")
    axes[0].set_title("Reference FID diagnostic dissipative fit")
    axes[0].set_xlabel("point")
    axes[0].set_ylabel("normalized amplitude")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(result.reference_freq_hz, _normalize_abs(result.reference_spectrum), lw=1.6, label="reference")
    axes[1].plot(result.reference_freq_hz, _normalize_abs(scaled_spec), lw=1.2, label="diagnostic fit")
    axes[1].set_title("Reference spectrum diagnostic comparison")
    axes[1].set_xlabel("frequency (Hz)")
    axes[1].set_ylabel("normalized |FFT|")
    axes[1].set_xlim(-30000, 30000)
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "status": "diagnostic_not_final_identification",
        "success": result.success,
        "message": result.message,
        "cost": result.cost,
        "nfev": result.nfev,
        "reference": str(result.reference_path),
        "n_points": result.n_points,
        "initial_rates": {
            "gamma_phi_s^-1": result.initial_rates.gamma_phi,
            "gamma_relax_s^-1": result.initial_rates.gamma_relax,
        },
        "fitted_rates": {
            "gamma_phi_s^-1": result.fitted_rates.gamma_phi,
            "gamma_relax_s^-1": result.fitted_rates.gamma_relax,
        },
        "complex_scale": {
            "real": float(result.complex_scale.real),
            "imag": float(result.complex_scale.imag),
        },
        "normalized_rmse": {
            "fid": result.normalized_rmse_fid,
            "spectrum": result.normalized_rmse_spectrum,
        },
        "physical_checks": {
            "max_trace_error": result.fitted.checks.max_trace_error,
            "max_hermiticity_error": result.fitted.checks.max_hermiticity_error,
            "min_eigenvalue": result.fitted.checks.min_eigenvalue,
        },
        "identifiability_warning": result.identifiability_warning,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_tomography_demo(figure: Path, json_path: Path) -> int:
    config = NMRConfig()
    rho_true = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T
    signals = simulate_tomography_signals(rho_true, config)
    result = reconstruct_density_matrix(signals, config, rho_true=rho_true)

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8), constrained_layout=True)
    _heatmap(axes[0, 0], rho_true.real, "True rho (real)")
    _heatmap(axes[0, 1], result.reconstructed_rho.real, "Reconstructed rho (real)")
    _heatmap(axes[1, 0], rho_true.imag, "True rho (imag)")
    _heatmap(axes[1, 1], result.reconstructed_rho.imag, "Reconstructed rho (imag)")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "fidelity": result.fidelity,
        "frobenius_error": result.frobenius_error,
        "residual_norm": result.residual_norm,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_tomography_pipeline_demo(
    figure: Path,
    json_path: Path,
    line_broadening_hz: float,
    integration_window_hz: float,
    diagnostic_search_hz: float,
    zero_fill_factor: int,
) -> int:
    config = NMRConfig()
    settings = ExtractionSettings(
        zero_fill_factor=zero_fill_factor,
        line_broadening_hz=line_broadening_hz,
        integration_window_hz=integration_window_hz,
        diagnostic_search_hz=diagnostic_search_hz,
    )
    rho_true = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T
    result = reconstruct_from_simulated_phase_series(rho_true, config, settings=settings)

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(9.8, 8), constrained_layout=True)
    _heatmap(axes[0, 0], rho_true.real, "True rho (real)")
    _heatmap(axes[0, 1], result.reconstructed_rho.real, "Reconstructed rho (real)")
    _heatmap(axes[1, 0], rho_true.imag, "True rho (imag)")
    _heatmap(axes[1, 1], result.reconstructed_rho.imag, "Reconstructed rho (imag)")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "fidelity": result.fidelity,
        "frobenius_error": result.frobenius_error,
        "residual_norm": result.residual_norm,
        "settings": {
            "zero_fill_factor": settings.zero_fill_factor,
            "line_broadening_hz": settings.line_broadening_hz,
            "integration_window_hz": settings.integration_window_hz,
            "diagnostic_search_hz": settings.diagnostic_search_hz,
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_nmr_experimental_tomography(
    manifest: Path,
    figure: Path,
    json_path: Path,
    line_broadening_hz: float,
    integration_window_hz: float,
    diagnostic_search_hz: float,
    zero_fill_factor: int,
) -> int:
    phase_files = load_phase_manifest(manifest)
    missing = [str(item["path"]) for item in phase_files if not Path(str(item["path"])).exists()]
    if missing:
        print("Manifest loaded, but the following experimental files are still missing:")
        for path in missing:
            print(path)
        print("\nFill the template with the real 7-phase `.tnt` files and run again.")
        return 0

    config = NMRConfig()
    settings = ExtractionSettings(
        zero_fill_factor=zero_fill_factor,
        line_broadening_hz=line_broadening_hz,
        integration_window_hz=integration_window_hz,
        diagnostic_search_hz=diagnostic_search_hz,
    )
    result = reconstruct_from_manifest(manifest, config=config, settings=settings)

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.2), constrained_layout=True)
    _heatmap(axes[0], result.reconstructed_rho.real, "Reconstructed rho (real)")
    _heatmap(axes[1], result.reconstructed_rho.imag, "Reconstructed rho (imag)")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "residual_norm": result.residual_norm,
        "trace_value_real": float(np.real(result.trace_value)),
        "manifest": str(manifest),
        "phase_files": [item.path for item in result.phase_measurements],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figure saved to: {figure}")
    print(f"Summary saved to: {json_path}")
    return 0


def cmd_export_research_config(output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    save_nmr_config_json(NMRConfig(), output)
    print(f"Configuration saved to: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "open-system-demo":
        return cmd_open_system_demo(args.figure, args.json)
    if args.command == "nmr-analyze-reference":
        return cmd_nmr_analyze_reference(args.reference)
    if args.command == "nmr-fit-reference":
        return cmd_nmr_fit_reference(args.reference, args.figure, args.json)
    if args.command == "nmr-simulate-reference":
        return cmd_nmr_simulate_reference(args.reference, args.figure)
    if args.command == "nmr-open-simulate":
        return cmd_nmr_open_simulate(
            args.figure,
            args.json,
            args.n_points,
            args.gamma_phi,
            args.gamma_relax,
        )
    if args.command == "nmr-synthetic-dissipation-fit":
        return cmd_nmr_synthetic_dissipation_fit(
            args.figure,
            args.json,
            args.n_points,
            args.true_gamma_phi,
            args.true_gamma_relax,
            args.initial_gamma_phi,
            args.initial_gamma_relax,
            args.noise_std,
            args.random_seed,
        )
    if args.command == "nmr-validation-suite":
        return cmd_nmr_validation_suite(
            args.figure,
            args.json,
            args.n_points,
            args.noise_levels,
            args.seeds,
            args.true_gamma_phi,
            args.true_gamma_relax,
            args.initial_gamma_phi,
            args.initial_gamma_relax,
        )
    if args.command == "nmr-fit-reference-dissipation":
        return cmd_nmr_fit_reference_dissipation(
            args.reference,
            args.figure,
            args.json,
            args.n_points,
            args.initial_gamma_phi,
            args.initial_gamma_relax,
        )
    if args.command == "nmr-tomography-demo":
        return cmd_nmr_tomography_demo(args.figure, args.json)
    if args.command == "nmr-tomography-pipeline-demo":
        return cmd_nmr_tomography_pipeline_demo(
            args.figure,
            args.json,
            args.line_broadening_hz,
            args.integration_window_hz,
            args.diagnostic_search_hz,
            args.zero_fill_factor,
        )
    if args.command == "nmr-experimental-tomography":
        return cmd_nmr_experimental_tomography(
            args.manifest,
            args.figure,
            args.json,
            args.line_broadening_hz,
            args.integration_window_hz,
            args.diagnostic_search_hz,
            args.zero_fill_factor,
        )
    if args.command == "export-research-config":
        return cmd_export_research_config(args.output)

    parser.error(f"Unknown command: {args.command}")
    return 2
