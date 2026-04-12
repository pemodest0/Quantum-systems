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
    coherent_superposition_state,
    mix_with_identity,
)
from oqs_control.platforms.na23_nmr.selective_pulses import (
    evaluate_selective_pulse,
    finite_selective_pulse_unitary,
    ideal_selective_rotation,
    population_transfer_probability,
    qst_monitor_selective_pulse,
    unitary_operator_fidelity,
)
from oqs_control.platforms.na23_nmr.tomography import state_fidelity


PAPER_ID = "spin32_qlogic_qst_2005"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Quantum logical operations for spin 3/2 quadrupolar nuclei monitored by quantum state tomography",
    "venue": "Journal of Magnetic Resonance",
    "year": 2005,
    "doi": "10.1016/j.jmr.2005.04.009",
    "role": "control_bridge",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def transition_rows(
    config: NMRConfig,
    transition_index: int,
    durations_s: np.ndarray,
    angle_rad: float,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    pair = config.transition_pairs[transition_index]
    for duration_s in durations_s:
        no_internal = evaluate_selective_pulse(
            config,
            transition_index=transition_index,
            angle_rad=angle_rad,
            duration_s=float(duration_s),
            include_quadrupolar_evolution=False,
        )
        with_internal = evaluate_selective_pulse(
            config,
            transition_index=transition_index,
            angle_rad=angle_rad,
            duration_s=float(duration_s),
            include_quadrupolar_evolution=True,
        )
        rows.append(
            {
                "transition": config.transition_labels[transition_index],
                "duration_s": float(duration_s),
                "duration_us": float(duration_s * 1e6),
                "operator_fidelity_no_internal": no_internal.operator_fidelity,
                "operator_fidelity_with_quadrupolar": with_internal.operator_fidelity,
                "mean_state_fidelity_no_internal": no_internal.mean_state_fidelity,
                "mean_state_fidelity_with_quadrupolar": with_internal.mean_state_fidelity,
                "population_transfer_no_internal": population_transfer_probability(
                    no_internal.actual_unitary,
                    pair[0],
                    pair[1],
                ),
                "population_transfer_with_quadrupolar": population_transfer_probability(
                    with_internal.actual_unitary,
                    pair[0],
                    pair[1],
                ),
            }
        )
    return rows


def safe_duration_us(rows: list[dict[str, float | str]], fidelity_threshold: float) -> float | None:
    safe = [
        float(row["duration_us"])
        for row in rows
        if float(row["operator_fidelity_with_quadrupolar"]) >= fidelity_threshold
    ]
    return max(safe) if safe else None


def initial_contiguous_safe_duration_us(
    rows: list[dict[str, float | str]],
    fidelity_threshold: float,
) -> float | None:
    last_safe: float | None = None
    ordered = sorted(rows, key=lambda row: float(row["duration_us"]))
    for row in ordered:
        if float(row["operator_fidelity_with_quadrupolar"]) >= fidelity_threshold:
            last_safe = float(row["duration_us"])
        else:
            break
    return last_safe


def plot_fidelity_vs_duration(
    path: Path,
    rows: list[dict[str, float | str]],
    transition_label: str,
) -> None:
    durations = np.array([float(row["duration_us"]) for row in rows], dtype=float)
    no_internal = np.array([float(row["operator_fidelity_no_internal"]) for row in rows], dtype=float)
    with_internal = np.array([float(row["operator_fidelity_with_quadrupolar"]) for row in rows], dtype=float)
    state_no = np.array([float(row["mean_state_fidelity_no_internal"]) for row in rows], dtype=float)
    state_with = np.array([float(row["mean_state_fidelity_with_quadrupolar"]) for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    ax.semilogx(durations, no_internal, marker="o", label="operator, no internal evolution")
    ax.semilogx(durations, with_internal, marker="s", label="operator, with quadrupolar evolution")
    ax.semilogx(durations, state_no, "--", marker="o", label="mean state, no internal evolution")
    ax.semilogx(durations, state_with, "--", marker="s", label="mean state, with quadrupolar evolution")
    ax.axhline(0.99, color="0.3", ls=":", lw=1.0, label="0.99 threshold")
    ax.set_title(f"Selective pi pulse fidelity vs duration ({transition_label})")
    ax.set_xlabel("pulse duration (us)")
    ax.set_ylabel("fidelity")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_population_transfer(
    path: Path,
    rows: list[dict[str, float | str]],
    transition_label: str,
) -> None:
    durations = np.array([float(row["duration_us"]) for row in rows], dtype=float)
    no_internal = np.array([float(row["population_transfer_no_internal"]) for row in rows], dtype=float)
    with_internal = np.array([float(row["population_transfer_with_quadrupolar"]) for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.semilogx(durations, no_internal, marker="o", label="no internal evolution")
    ax.semilogx(durations, with_internal, marker="s", label="with quadrupolar evolution")
    ax.set_title(f"Population transfer for a selective pi pulse ({transition_label})")
    ax.set_xlabel("pulse duration (us)")
    ax.set_ylabel("transition population-transfer probability")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def all_transition_fidelity_rows(
    config: NMRConfig,
    durations_s: np.ndarray,
    angle_rad: float,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for transition_index, label in enumerate(config.transition_labels):
        for duration_s in durations_s:
            result = evaluate_selective_pulse(
                config,
                transition_index=transition_index,
                angle_rad=angle_rad,
                duration_s=float(duration_s),
                include_quadrupolar_evolution=True,
            )
            rows.append(
                {
                    "transition": label,
                    "duration_s": float(duration_s),
                    "duration_us": float(duration_s * 1e6),
                    "operator_fidelity_with_quadrupolar": result.operator_fidelity,
                    "mean_state_fidelity_with_quadrupolar": result.mean_state_fidelity,
                }
            )
    return rows


def plot_all_transition_fidelities(
    path: Path,
    rows: list[dict[str, float | str]],
    labels: tuple[str, ...],
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for label in labels:
        subset = [row for row in rows if row["transition"] == label]
        durations = np.array([float(row["duration_us"]) for row in subset], dtype=float)
        fidelity = np.array(
            [float(row["operator_fidelity_with_quadrupolar"]) for row in subset],
            dtype=float,
        )
        ax.semilogx(durations, fidelity, marker="o", label=label)
    ax.axhline(0.99, color="0.3", ls=":", lw=1.0)
    ax.set_title("Quadrupolar evolution impact across selective transitions")
    ax.set_xlabel("pulse duration (us)")
    ax.set_ylabel("operator fidelity with internal evolution")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_qst_density_monitor(
    path: Path,
    target_state: np.ndarray,
    actual_state: np.ndarray,
    reconstructed_state: np.ndarray,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.8), constrained_layout=True)
    payload = [
        ("ideal target Re rho", np.real(target_state)),
        ("actual pulse Re rho", np.real(actual_state)),
        ("QST reconstructed Re rho", np.real(reconstructed_state)),
    ]
    vmax = max(float(np.max(np.abs(item[1]))) for item in payload)
    for ax, (title, matrix) in zip(axes, payload):
        image = ax.imshow(matrix, vmin=-vmax, vmax=vmax, cmap="coolwarm")
        ax.set_title(title)
        ax.set_xlabel("ket index")
        ax.set_ylabel("bra index")
    fig.colorbar(image, ax=axes, shrink=0.85)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    config = NMRConfig(n_acq=256, n_zf=256)
    transition_index = 1
    transition_label = config.transition_labels[transition_index]
    transition_pair = config.transition_pairs[transition_index]
    angle_rad = np.pi
    durations_s = np.array([4, 8, 12, 20, 40, 80, 160, 320, 640], dtype=float) * 1e-6

    ct_rows = transition_rows(config, transition_index, durations_s, angle_rad)
    all_rows = all_transition_fidelity_rows(config, durations_s, angle_rad)

    qst_duration_s = 160e-6
    ideal_gate = ideal_selective_rotation(config.dim, transition_pair, angle_rad)
    actual_gate = finite_selective_pulse_unitary(
        config,
        transition_pair,
        angle_rad,
        duration_s=qst_duration_s,
        include_quadrupolar_evolution=True,
    )
    initial_state = mix_with_identity(coherent_superposition_state(config.dim), mixing=0.04)
    target_state = ideal_gate @ initial_state @ ideal_gate.conj().T
    actual_state, reconstructed_state, qst_fidelity = qst_monitor_selective_pulse(
        config,
        actual_gate,
        initial_state,
    )
    target_vs_actual_fidelity = state_fidelity(target_state, actual_state)
    qst_target_fidelity = state_fidelity(target_state, reconstructed_state)

    figures = {
        "selective_pulse_fidelity_vs_duration": figure_dir / "selective_pulse_fidelity_vs_duration.png",
        "population_transfer_vs_duration": figure_dir / "population_transfer_vs_duration.png",
        "all_transition_fidelity_comparison": figure_dir / "all_transition_fidelity_comparison.png",
        "qst_density_monitor": figure_dir / "qst_density_monitor.png",
    }
    plot_fidelity_vs_duration(figures["selective_pulse_fidelity_vs_duration"], ct_rows, transition_label)
    plot_population_transfer(figures["population_transfer_vs_duration"], ct_rows, transition_label)
    plot_all_transition_fidelities(figures["all_transition_fidelity_comparison"], all_rows, config.transition_labels)
    plot_qst_density_monitor(figures["qst_density_monitor"], target_state, actual_state, reconstructed_state)

    no_internal_min = min(float(row["operator_fidelity_no_internal"]) for row in ct_rows)
    with_internal_min = min(float(row["operator_fidelity_with_quadrupolar"]) for row in ct_rows)
    with_internal_at_qst = next(
        float(row["operator_fidelity_with_quadrupolar"])
        for row in ct_rows
        if abs(float(row["duration_s"]) - qst_duration_s) < 1e-15
    )

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "target_transition": {
            "label": transition_label,
            "pair": list(transition_pair),
            "pulse_angle_rad": float(angle_rad),
            "logical_interpretation": "selective pi pulse swaps the two addressed spin-3/2 levels",
        },
        "fidelity_summary": {
            "min_operator_fidelity_no_internal": no_internal_min,
            "min_operator_fidelity_with_quadrupolar": with_internal_min,
            "initial_contiguous_safe_duration_us_at_operator_fidelity_0p999": initial_contiguous_safe_duration_us(
                ct_rows,
                0.999,
            ),
            "initial_contiguous_safe_duration_us_at_operator_fidelity_0p99": initial_contiguous_safe_duration_us(
                ct_rows,
                0.99,
            ),
            "initial_contiguous_safe_duration_us_at_operator_fidelity_0p95": initial_contiguous_safe_duration_us(
                ct_rows,
                0.95,
            ),
            "max_sampled_revival_duration_us_at_operator_fidelity_0p999": safe_duration_us(ct_rows, 0.999),
            "max_sampled_revival_duration_us_at_operator_fidelity_0p99": safe_duration_us(ct_rows, 0.99),
            "operator_fidelity_with_quadrupolar_at_qst_duration": with_internal_at_qst,
        },
        "ct_duration_table": ct_rows,
        "all_transition_duration_table": all_rows,
        "qst_monitor": {
            "pulse_duration_s": qst_duration_s,
            "target_vs_actual_state_fidelity": float(target_vs_actual_fidelity),
            "actual_vs_qst_reconstructed_fidelity": float(qst_fidelity),
            "target_vs_qst_reconstructed_fidelity": float(qst_target_fidelity),
            "operator_fidelity_target_vs_actual": unitary_operator_fidelity(ideal_gate, actual_gate),
        },
        "scientific_interpretation": {
            "captures": [
                "a selective transition pulse is represented as a two-level rotation embedded in the spin-3/2 manifold",
                "finite pulse duration exposes the operation to quadrupolar evolution during the control window",
                "QST can monitor the resulting state after the imperfect selective operation",
            ],
            "does_not_capture": [
                "no shaped pulse optimization is included yet",
                "no experimental RF calibration or amplifier response is modeled",
                "the logical gate library of the paper is not fully reproduced; this is the minimal selective-pulse control benchmark",
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
            "transition_labels": list(config.transition_labels),
            "transition_pairs": [list(pair) for pair in config.transition_pairs],
        },
        "implemented_equations": {
            "ideal_selective_rotation": "U_ideal = exp[-i theta/2 (cos phi X_ij + sin phi Y_ij)]",
            "finite_pulse_without_internal": "U = exp[-i H_control tau]",
            "finite_pulse_with_internal": "U = exp[-i (H_control + H_free_in_selected_carrier_frame) tau]",
            "operator_fidelity": "F_op = |Tr(U_target^dagger U_actual)|^2 / d^2",
            "qst_monitor": "signals = tomography_pulses(U rho U^dagger), then A vec(rho)=b",
        },
        "assumptions": [
            "The central transition is used as the minimal logical-operation benchmark.",
            "The ideal target is a perfect embedded two-level pi rotation.",
            "The no-internal-evolution case represents the approximation often made for control pulses.",
            "The with-internal-evolution case keeps quadrupolar evolution during the pulse in the selected carrier frame.",
            "Long-duration high-fidelity points are treated as sampled phase revivals, not as a monotonic safe operating window.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": {
            "target_transition": transition_label,
            "min_operator_fidelity_no_internal": no_internal_min,
            "min_operator_fidelity_with_quadrupolar": with_internal_min,
            "initial_contiguous_safe_duration_us_at_operator_fidelity_0p99": metrics["fidelity_summary"][
                "initial_contiguous_safe_duration_us_at_operator_fidelity_0p99"
            ],
            "qst_target_vs_actual_state_fidelity": float(target_vs_actual_fidelity),
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# Quantum Logical Operations For Spin 3/2 Quadrupolar Nuclei Monitored By QST",
                "",
                "This run implements a minimal selective-pulse control benchmark for",
                "a spin-3/2 quadrupolar nucleus.",
                "",
                f"Target transition: `{transition_label}` with pair `{transition_pair}`.",
                f"No-internal minimum operator fidelity: `{no_internal_min:.8f}`.",
                f"With-quadrupolar minimum operator fidelity: `{with_internal_min:.8f}`.",
                f"QST-duration target-vs-actual state fidelity: `{target_vs_actual_fidelity:.8f}`.",
                "",
                "The result is a control benchmark, not a full reproduction of every",
                "logical gate from the paper.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the spin-3/2 quantum logic/QST Paper D target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
