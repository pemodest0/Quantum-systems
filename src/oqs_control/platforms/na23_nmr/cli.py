from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .analysis import fft_spectrum, flatten_first_trace, summarize_reference
from .config import NMRConfig
from .config_io import save_config_json
from .experimental_tomography import (
    ExtractionSettings,
    load_phase_manifest,
    reconstruct_from_manifest,
    reconstruct_from_simulated_phase_series,
)
from .fitting import fit_reference_spectrum
from .io import read_tnt
from .simulation import simulate_reference_experiment
from .tomography import reconstruct_density_matrix, simulate_tomography_signals


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_reference_path() -> Path:
    return project_root() / "data" / "reference" / "Referential2.tnt"


def default_outputs_dir() -> Path:
    outputs = project_root() / "outputs"
    outputs.mkdir(exist_ok=True)
    return outputs


def _heatmap(ax: plt.Axes, mat: np.ndarray, title: str) -> None:
    image = ax.imshow(mat, cmap="coolwarm")
    ax.set_title(title)
    ax.set_xlabel("coluna")
    ax.set_ylabel("linha")
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="na23-nmr",
        description="Python-first 23Na NMR research toolkit derived from the available MATLAB material.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze-reference", help="Analyze the reference TNT file.")
    p_analyze.add_argument("--reference", type=Path, default=default_reference_path())

    p_sim = sub.add_parser("simulate-reference", help="Simulate and compare against the reference spectrum.")
    p_sim.add_argument("--reference", type=Path, default=default_reference_path())
    p_sim.add_argument("--output", type=Path, default=default_outputs_dir() / "reference_vs_simulation.png")

    p_fit = sub.add_parser("fit-reference", help="Fit nuQ/pulse width/line broadening to the reference spectrum.")
    p_fit.add_argument("--reference", type=Path, default=default_reference_path())
    p_fit.add_argument("--figure", type=Path, default=default_outputs_dir() / "reference_fit.png")
    p_fit.add_argument("--json", type=Path, default=default_outputs_dir() / "reference_fit.json")

    p_tomo = sub.add_parser("tomography-demo", help="Run the direct tomography demo on synthetic signals.")
    p_tomo.add_argument("--figure", type=Path, default=default_outputs_dir() / "tomography_demo.png")
    p_tomo.add_argument("--json", type=Path, default=default_outputs_dir() / "tomography_demo.json")

    p_pipe = sub.add_parser(
        "tomography-pipeline-demo",
        help="Run end-to-end tomography from synthetic FIDs and spectral extraction.",
    )
    p_pipe.add_argument("--figure", type=Path, default=default_outputs_dir() / "tomography_pipeline_demo.png")
    p_pipe.add_argument("--json", type=Path, default=default_outputs_dir() / "tomography_pipeline_demo.json")
    p_pipe.add_argument("--line-broadening-hz", type=float, default=20.0)
    p_pipe.add_argument("--integration-window-hz", type=float, default=1000.0)
    p_pipe.add_argument("--diagnostic-search-hz", type=float, default=1800.0)
    p_pipe.add_argument("--zero-fill-factor", type=int, default=4)

    p_exp = sub.add_parser(
        "experimental-tomography",
        help="Run tomography from a 7-phase manifest of real TNT files.",
    )
    p_exp.add_argument(
        "--manifest",
        type=Path,
        default=project_root() / "examples" / "experimental_tomography_manifest.template.json",
    )
    p_exp.add_argument("--figure", type=Path, default=default_outputs_dir() / "experimental_tomography.png")
    p_exp.add_argument("--json", type=Path, default=default_outputs_dir() / "experimental_tomography.json")
    p_exp.add_argument("--line-broadening-hz", type=float, default=20.0)
    p_exp.add_argument("--integration-window-hz", type=float, default=1000.0)
    p_exp.add_argument("--diagnostic-search-hz", type=float, default=1800.0)
    p_exp.add_argument("--zero-fill-factor", type=int, default=4)

    p_cfg = sub.add_parser("export-config", help="Export the default Python configuration to JSON.")
    p_cfg.add_argument("--output", type=Path, default=project_root() / "examples" / "default_config.json")

    return parser


def cmd_analyze_reference(reference: Path) -> int:
    print(json.dumps(summarize_reference(reference), indent=2, ensure_ascii=False))
    return 0


def cmd_simulate_reference(reference: Path, output: Path) -> int:
    config = NMRConfig()
    sim = simulate_reference_experiment(config)

    ref = read_tnt(reference)
    ref_fid = flatten_first_trace(ref)
    ref_freq_hz, ref_spec = fft_spectrum(ref_fid, dwell_time=config.dwell_time)
    sim_norm = np.abs(sim.spectrum) / np.max(np.abs(sim.spectrum))
    ref_norm = np.abs(ref_spec) / np.max(np.abs(ref_spec))

    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
    axes[0].plot(sim.time_s * 1e3, sim.fid.real, lw=1.3, label="sim real")
    axes[0].plot(sim.time_s * 1e3, sim.fid.imag, lw=1.0, label="sim imag", alpha=0.8)
    axes[0].set_title("FID simulado")
    axes[0].set_xlabel("tempo (ms)")
    axes[0].set_ylabel("amplitude (u.a.)")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(ref_freq_hz, ref_norm, lw=1.8, label="experimento")
    axes[1].plot(sim.freq_hz, sim_norm, lw=1.3, label="simulacao")
    axes[1].set_title("Comparacao de espectros")
    axes[1].set_xlabel("frequencia (Hz)")
    axes[1].set_ylabel("|FFT| normalizada")
    axes[1].set_xlim(-30000, 30000)
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    print(f"Figura salva em: {output}")
    return 0


def cmd_fit_reference(reference: Path, figure: Path, json_path: Path) -> int:
    fit = fit_reference_spectrum(reference)
    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.plot(fit.freq_hz, fit.reference_magnitude, lw=1.8, label="experimento")
    ax.plot(fit.freq_hz, fit.fitted_magnitude, lw=1.4, label="ajuste")
    ax.set_title("Ajuste do espectro de referencia")
    ax.set_xlabel("frequencia (Hz)")
    ax.set_ylabel("|FFT| normalizada")
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
        "fit_window_hz": fit.fit_window_hz,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figura salva em: {figure}")
    print(f"Resumo salvo em: {json_path}")
    return 0


def cmd_tomography_demo(figure: Path, json_path: Path) -> int:
    config = NMRConfig()
    rho_true = config.u_pi2 @ config.rho_eq @ config.u_pi2.conj().T
    signals = simulate_tomography_signals(rho_true, config)
    result = reconstruct_density_matrix(signals, config, rho_true=rho_true)

    figure.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8), constrained_layout=True)
    _heatmap(axes[0, 0], rho_true.real, "rho verdadeira - parte real")
    _heatmap(axes[0, 1], result.reconstructed_rho.real, "rho reconstruida - parte real")
    _heatmap(axes[1, 0], rho_true.imag, "rho verdadeira - parte imag")
    _heatmap(axes[1, 1], result.reconstructed_rho.imag, "rho reconstruida - parte imag")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "fidelity": result.fidelity,
        "frobenius_error": result.frobenius_error,
        "residual_norm": result.residual_norm,
        "trace_value_real": float(np.real(result.trace_value)),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figura salva em: {figure}")
    print(f"Resumo salvo em: {json_path}")
    return 0


def cmd_tomography_pipeline_demo(
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
    _heatmap(axes[0, 0], rho_true.real, "rho verdadeira - parte real")
    _heatmap(axes[0, 1], result.reconstructed_rho.real, "rho reconstruida - parte real")
    _heatmap(axes[1, 0], rho_true.imag, "rho verdadeira - parte imag")
    _heatmap(axes[1, 1], result.reconstructed_rho.imag, "rho reconstruida - parte imag")
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    payload = {
        "fidelity": result.fidelity,
        "frobenius_error": result.frobenius_error,
        "residual_norm": result.residual_norm,
        "trace_value_real": float(np.real(result.trace_value)),
        "extraction_settings": {
            "zero_fill_factor": settings.zero_fill_factor,
            "line_broadening_hz": settings.line_broadening_hz,
            "integration_window_hz": settings.integration_window_hz,
            "diagnostic_search_hz": settings.diagnostic_search_hz,
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Figura salva em: {figure}")
    print(f"Resumo salvo em: {json_path}")
    return 0


def cmd_experimental_tomography(
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
        print("Manifest carregado, mas ainda faltam arquivos experimentais:")
        for path in missing:
            print(path)
        print("\nPreencha o template com os 7 arquivos `.tnt` reais e rode novamente.")
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
    _heatmap(axes[0], result.reconstructed_rho.real, "rho reconstruida - parte real")
    _heatmap(axes[1], result.reconstructed_rho.imag, "rho reconstruida - parte imag")
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
    print(f"Figura salva em: {figure}")
    print(f"Resumo salvo em: {json_path}")
    return 0


def cmd_export_config(output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    save_config_json(NMRConfig(), output)
    print(f"Configuracao salva em: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze-reference":
        return cmd_analyze_reference(args.reference)
    if args.command == "simulate-reference":
        return cmd_simulate_reference(args.reference, args.output)
    if args.command == "fit-reference":
        return cmd_fit_reference(args.reference, args.figure, args.json)
    if args.command == "tomography-demo":
        return cmd_tomography_demo(args.figure, args.json)
    if args.command == "tomography-pipeline-demo":
        return cmd_tomography_pipeline_demo(
            args.figure,
            args.json,
            args.line_broadening_hz,
            args.integration_window_hz,
            args.diagnostic_search_hz,
            args.zero_fill_factor,
        )
    if args.command == "experimental-tomography":
        return cmd_experimental_tomography(
            args.manifest,
            args.figure,
            args.json,
            args.line_broadening_hz,
            args.integration_window_hz,
            args.diagnostic_search_hz,
            args.zero_fill_factor,
        )
    if args.command == "export-config":
        return cmd_export_config(args.output)

    parser.error(f"Unknown command: {args.command}")
    return 2
