from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

from oqs_control.open_systems.lindblad import density_matrix_to_vector
from oqs_control.platforms.na23_nmr.algebraic_spin32 import (
    coherence_order_weights,
    deviation_density,
    free_liouvillian,
    rf_pulse_unitary,
    signal_energy,
    simulate_algebraic_one_pulse_fid,
    trace_row,
    unitary_superoperator,
)
from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.simulation import simulate_fid


PAPER_ID = "spin32_algebraic_2004"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Algebraic description of spin 3/2 dynamics in NMR experiments",
    "authors": "C. Tanase and F. E. Boada",
    "venue": "Journal of Magnetic Resonance",
    "volume": "173",
    "issue": "2",
    "pages": "236-253",
    "year": 2005,
    "doi": "10.1016/j.jmr.2004.12.009",
    "note": "The project keeps the original requested paper_id spin32_algebraic_2004 because the DOI and accepted manuscript timeline use 2004, while the journal issue is 2005.",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def no_decay_params() -> np.ndarray:
    return np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
        ],
        dtype=float,
    )


def plot_hilbert_vs_liouville(
    path: Path,
    time_s: np.ndarray,
    hilbert_fid: np.ndarray,
    liouville_fid: np.ndarray,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 7.0), sharex=True, constrained_layout=True)
    axes[0].plot(time_s * 1e3, np.real(hilbert_fid), label="Hilbert density propagation", lw=1.4)
    axes[0].plot(time_s * 1e3, np.real(liouville_fid), "--", label="Liouville superoperator", lw=1.2)
    axes[0].set_ylabel("Re FID")
    axes[0].set_title("One-pulse FID: density-matrix propagation vs algebraic superoperator")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].semilogy(time_s * 1e3, np.abs(hilbert_fid - liouville_fid) + 1e-30, lw=1.2)
    axes[1].set_xlabel("time (ms)")
    axes[1].set_ylabel("|difference|")
    axes[1].grid(alpha=0.25, which="both")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def coherence_pathway(config: NMRConfig) -> tuple[list[str], list[dict[int, float]]]:
    rho = deviation_density(config)
    free_time_s = 90e-6
    pulse_x = rf_pulse_unitary(config, phase_rad=0.0, include_bloch_siegert=True)
    pulse_y = rf_pulse_unitary(config, phase_rad=np.pi / 2.0, include_bloch_siegert=True)
    free_u = expm(-1j * config.h_free * free_time_s)

    labels = ["thermal deviation", "after x pi/2", "after free evolution", "after y pi/2", "after second free"]
    states = [rho]
    rho = pulse_x @ rho @ pulse_x.conj().T
    states.append(rho)
    rho = free_u @ rho @ free_u.conj().T
    states.append(rho)
    rho = pulse_y @ rho @ pulse_y.conj().T
    states.append(rho)
    rho = free_u @ rho @ free_u.conj().T
    states.append(rho)

    weights = [coherence_order_weights(state, config.m_vals) for state in states]
    return labels, weights


def plot_coherence_pathways(path: Path, labels: list[str], weights: list[dict[int, float]]) -> None:
    orders = list(range(-3, 4))
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels), dtype=float)
    fig, ax = plt.subplots(figsize=(10.0, 5.5), constrained_layout=True)
    colors = plt.cm.coolwarm(np.linspace(0.08, 0.92, len(orders)))
    for color, order in zip(colors, orders):
        values = np.array([entry.get(order, 0.0) for entry in weights], dtype=float)
        ax.bar(x, values, bottom=bottom, label=f"q={order}", color=color)
        bottom += values
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("normalized Frobenius weight")
    ax.set_title("Coherence-order redistribution under spin-3/2 RF/free evolution")
    ax.legend(ncols=4, fontsize=8)
    ax.grid(alpha=0.2, axis="y")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def b0_b1_energy_map(config: NMRConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    b0_offsets_hz = np.linspace(-2_500.0, 2_500.0, 31)
    b1_scales = np.linspace(0.55, 1.45, 31)
    energy = np.zeros((b1_scales.size, b0_offsets_hz.size), dtype=float)
    for i, b1_scale in enumerate(b1_scales):
        for j, b0_offset_hz in enumerate(b0_offsets_hz):
            result = simulate_algebraic_one_pulse_fid(
                config,
                n_points=96,
                b0_offset_hz=float(b0_offset_hz),
                b1_scale=float(b1_scale),
            )
            energy[i, j] = signal_energy(result.fid)
    nominal = energy[int(b1_scales.size // 2), int(b0_offsets_hz.size // 2)]
    return b0_offsets_hz, b1_scales, energy / max(nominal, 1e-30)


def plot_b0_b1_map(
    path: Path,
    b0_offsets_hz: np.ndarray,
    b1_scales: np.ndarray,
    normalized_energy: np.ndarray,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 6.0), constrained_layout=True)
    image = ax.imshow(
        normalized_energy,
        origin="lower",
        aspect="auto",
        extent=[
            float(b0_offsets_hz[0]),
            float(b0_offsets_hz[-1]),
            float(b1_scales[0]),
            float(b1_scales[-1]),
        ],
        cmap="magma",
        vmin=float(np.percentile(normalized_energy, 2)),
        vmax=float(np.percentile(normalized_energy, 98)),
    )
    ax.set_title("One-pulse FID energy sensitivity to B0 offset and B1 scale")
    ax.set_xlabel("B0 offset during pulse and acquisition (Hz)")
    ax.set_ylabel("B1 scale")
    fig.colorbar(image, ax=ax, label="normalized FID energy")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def factorization_errors(config: NMRConfig) -> tuple[np.ndarray, np.ndarray]:
    pulse_u = rf_pulse_unitary(config)
    pulse_s = unitary_superoperator(pulse_u)
    rho_vec = density_matrix_to_vector(deviation_density(config))
    times_s = np.linspace(0.0, 1.5e-3, 80)
    errors = np.zeros_like(times_s)
    for idx, time_s in enumerate(times_s):
        free_u = expm(-1j * config.h_free * float(time_s))
        direct_s = unitary_superoperator(free_u @ pulse_u)
        factored_s = expm(free_liouvillian(config) * float(time_s)) @ pulse_s
        errors[idx] = float(np.linalg.norm((direct_s - factored_s) @ rho_vec))
    return times_s, errors


def plot_factorization(path: Path, times_s: np.ndarray, errors: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    ax.semilogy(times_s * 1e3, errors + 1e-30, lw=1.4)
    ax.set_title("Superoperator factorization check: F(t) P vs direct unitary composition")
    ax.set_xlabel("free evolution time after pulse (ms)")
    ax.set_ylabel("state-vector norm error")
    ax.grid(alpha=0.25, which="both")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig(n_acq=512, n_zf=512, decay_params=no_decay_params())
    hilbert_fid = simulate_fid(config, n_points=config.n_acq)
    liouville = simulate_algebraic_one_pulse_fid(config, n_points=config.n_acq)
    time_s = np.arange(config.n_acq, dtype=float) * config.dwell_time

    labels, coherence_weights = coherence_pathway(config)
    b0_offsets_hz, b1_scales, normalized_energy = b0_b1_energy_map(config)
    factor_times_s, factor_errors = factorization_errors(config)

    figures = {
        "hilbert_vs_liouville_fid": figure_dir / "hilbert_vs_liouville_fid.png",
        "coherence_order_pathways": figure_dir / "coherence_order_pathways.png",
        "b0_b1_energy_map": figure_dir / "b0_b1_energy_map.png",
        "superoperator_factorization_error": figure_dir / "superoperator_factorization_error.png",
    }
    plot_hilbert_vs_liouville(figures["hilbert_vs_liouville_fid"], time_s, hilbert_fid, liouville.fid)
    plot_coherence_pathways(figures["coherence_order_pathways"], labels, coherence_weights)
    plot_b0_b1_map(figures["b0_b1_energy_map"], b0_offsets_hz, b1_scales, normalized_energy)
    plot_factorization(figures["superoperator_factorization_error"], factor_times_s, factor_errors)

    trace_errors = np.abs(np.trace(liouville.states, axis1=1, axis2=2) - 1.0)
    hermiticity_errors = np.max(
        np.abs(liouville.states - np.conjugate(np.swapaxes(liouville.states, 1, 2))),
        axis=(1, 2),
    )
    weights_after_first_pulse = coherence_weights[1]
    single_quantum_weight = sum(
        value for order, value in weights_after_first_pulse.items() if abs(order) == 1
    )

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "hilbert_vs_liouville": {
            "max_abs_fid_error": float(np.max(np.abs(hilbert_fid - liouville.fid))),
            "rms_abs_fid_error": float(np.sqrt(np.mean(np.abs(hilbert_fid - liouville.fid) ** 2))),
        },
        "physical_checks": {
            "max_trace_error": float(np.max(trace_errors)),
            "max_hermiticity_error": float(np.max(hermiticity_errors)),
            "trace_row_invariance_error": float(
                np.linalg.norm(trace_row(config.dim) @ unitary_superoperator(config.u_dwell) - trace_row(config.dim))
            ),
        },
        "coherence_pathways": {
            "labels": labels,
            "orders": [str(order) for order in range(-3, 4)],
            "weights": [{str(order): value for order, value in entry.items()} for entry in coherence_weights],
            "single_quantum_weight_after_first_pulse": float(single_quantum_weight),
        },
        "b0_b1_sensitivity": {
            "b0_offset_min_hz": float(b0_offsets_hz[0]),
            "b0_offset_max_hz": float(b0_offsets_hz[-1]),
            "b1_scale_min": float(b1_scales[0]),
            "b1_scale_max": float(b1_scales[-1]),
            "normalized_energy_min": float(np.min(normalized_energy)),
            "normalized_energy_max": float(np.max(normalized_energy)),
            "max_relative_bias_from_nominal": float(np.max(np.abs(normalized_energy - 1.0))),
        },
        "superoperator_factorization": {
            "max_state_vector_error": float(np.max(factor_errors)),
            "rms_state_vector_error": float(np.sqrt(np.mean(factor_errors**2))),
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
            "t_pi2_s": config.t_pi2,
            "dwell_time_s": config.dwell_time,
            "n_acq": config.n_acq,
        },
        "implemented_equations": {
            "vectorization": "vec(rho) uses column-major order",
            "unitary_superoperator": "vec(U rho U^dagger) = (U* kron U) vec(rho)",
            "liouville_dynamics": "d vec(rho) / dt = L vec(rho)",
            "detector": "s(t) = Tr(rho(t) D) = d vec(rho(t))",
            "factorization": "vec(rho(t)) = F(t) P vec(rho0) for pulse P followed by free evolution F(t)",
            "coherence_order": "q = m_bra - m_ket",
        },
        "assumptions": [
            "Relaxation is disabled for the Hilbert-vs-Liouville equivalence check.",
            "B0/B1 sensitivity is synthetic and intended as an algebraic bias benchmark.",
            "The reproduction targets an equivalent observable rather than a digitized paper figure.",
            "The paper_id keeps the requested 2004 label although the journal issue is 2005.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "summary": {
            "max_abs_fid_error": metrics["hilbert_vs_liouville"]["max_abs_fid_error"],
            "single_quantum_weight_after_first_pulse": single_quantum_weight,
            "max_b0_b1_relative_bias": metrics["b0_b1_sensitivity"]["max_relative_bias_from_nominal"],
            "max_factorization_error": metrics["superoperator_factorization"]["max_state_vector_error"],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the spin-3/2 algebraic NMR target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

