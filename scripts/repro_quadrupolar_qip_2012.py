from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.qst_relaxation import add_tomography_noise
from oqs_control.platforms.na23_nmr.quadrupolar_qip import (
    COMPUTATIONAL_BASIS,
    decompose_in_product_operator_basis,
    deviation_fidelity,
    pseudo_pure_state,
    quadrupolar_traceless_operator,
    reconstruct_from_product_coefficients,
    run_grover_search,
)
from oqs_control.platforms.na23_nmr.tomography import (
    reconstruct_density_matrix,
    simulate_tomography_signals,
    state_fidelity,
)


PAPER_ID = "quadrupolar_qip_2012"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Quantum information processing by nuclear magnetic resonance on quadrupolar nuclei",
    "venue": "Philosophical Transactions of the Royal Society A",
    "year": 2012,
    "doi": "10.1098/rsta.2011.0365",
    "role": "quadrupolar_qip_bridge",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def nonzero_coefficients(coefficients: dict[str, float], threshold: float = 1e-12) -> dict[str, float]:
    return {
        label: float(value)
        for label, value in coefficients.items()
        if abs(float(value)) > threshold
    }


def coefficient_grid(coefficients: dict[str, float]) -> np.ndarray:
    rows = ("I", "X", "Y", "Z")
    cols = ("I", "X", "Y", "Z")
    return np.array([[coefficients[left + right] for right in cols] for left in rows], dtype=float)


def plot_product_operator_decomposition(
    path: Path,
    iz_coeffs: dict[str, float],
    q_coeffs: dict[str, float],
) -> None:
    rows = ("I", "X", "Y", "Z")
    cols = ("I", "X", "Y", "Z")
    matrices = [
        ("Iz in logical-product basis", coefficient_grid(iz_coeffs)),
        ("3 Iz^2 - I(I+1) I", coefficient_grid(q_coeffs)),
    ]
    vmax = max(float(np.max(np.abs(matrix))) for _, matrix in matrices)

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), constrained_layout=True)
    for ax, (title, matrix) in zip(axes, matrices):
        image = ax.imshow(matrix, vmin=-vmax, vmax=vmax, cmap="coolwarm")
        ax.set_title(title)
        ax.set_xticks(range(4), cols)
        ax.set_yticks(range(4), rows)
        ax.set_xlabel("right logical qubit operator")
        ax.set_ylabel("left logical qubit operator")
        for row in range(4):
            for col in range(4):
                value = matrix[row, col]
                if abs(value) > 1e-10:
                    ax.text(col, row, f"{value:.2g}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=axes, shrink=0.82)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_grover_populations(path: Path, population_matrix: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 5.4), constrained_layout=True)
    image = ax.imshow(population_matrix, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_title("Two-qubit Grover search on the spin-3/2 logical manifold")
    ax.set_xlabel("measured computational basis state")
    ax.set_ylabel("marked state")
    ax.set_xticks(range(4), COMPUTATIONAL_BASIS)
    ax.set_yticks(range(4), COMPUTATIONAL_BASIS)
    for row in range(4):
        for col in range(4):
            ax.text(col, row, f"{population_matrix[row, col]:.2f}", ha="center", va="center", color="white")
    fig.colorbar(image, ax=ax, label="final population")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_pseudopure_visibility(path: Path, epsilons: np.ndarray) -> None:
    marked_population = 0.25 + 0.75 * epsilons
    unmarked_population = 0.25 - 0.25 * epsilons
    contrast = marked_population - unmarked_population

    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.semilogx(epsilons, marked_population, label="marked-state population")
    ax.semilogx(epsilons, unmarked_population, label="each unmarked population")
    ax.semilogx(epsilons, contrast, label="NMR deviation contrast")
    ax.set_title("Pseudo-pure Grover visibility")
    ax.set_xlabel("pseudo-pure polarization parameter epsilon")
    ax.set_ylabel("population / contrast")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def qst_noise_rows(
    config: NMRConfig,
    target_state: np.ndarray,
    noise_levels: tuple[float, ...],
    seeds: tuple[int, ...],
) -> list[dict[str, float]]:
    clean_signals = simulate_tomography_signals(target_state, config)
    rows: list[dict[str, float]] = []
    for noise_std in noise_levels:
        state_fids: list[float] = []
        dev_fids: list[float] = []
        residuals: list[float] = []
        for seed in seeds:
            rng = np.random.default_rng(seed)
            measured = add_tomography_noise(clean_signals, noise_std, rng)
            qst = reconstruct_density_matrix(measured, config, rho_true=target_state)
            state_fids.append(state_fidelity(target_state, qst.reconstructed_rho))
            dev_fids.append(deviation_fidelity(qst.reconstructed_rho, target_state))
            residuals.append(float(qst.residual_norm))
        rows.append(
            {
                "noise_std": float(noise_std),
                "state_fidelity_mean": float(np.mean(state_fids)),
                "state_fidelity_std": float(np.std(state_fids)),
                "deviation_fidelity_mean": float(np.mean(dev_fids)),
                "deviation_fidelity_std": float(np.std(dev_fids)),
                "residual_norm_mean": float(np.mean(residuals)),
            }
        )
    return rows


def plot_qst_noise(path: Path, rows: list[dict[str, float]]) -> None:
    x = np.array([row["noise_std"] for row in rows], dtype=float)
    state_mean = np.array([row["state_fidelity_mean"] for row in rows], dtype=float)
    state_std = np.array([row["state_fidelity_std"] for row in rows], dtype=float)
    dev_mean = np.array([row["deviation_fidelity_mean"] for row in rows], dtype=float)
    dev_std = np.array([row["deviation_fidelity_std"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.errorbar(x, state_mean, yerr=state_std, marker="o", capsize=3, label="state fidelity")
    ax.errorbar(x, dev_mean, yerr=dev_std, marker="s", capsize=3, label="deviation-density fidelity")
    ax.set_title("QST sensitivity for a pseudo-pure Grover output")
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
    q_op = quadrupolar_traceless_operator(config.i_spin, config.i_z2)
    iz_coeffs = decompose_in_product_operator_basis(config.i_z)
    q_coeffs = decompose_in_product_operator_basis(q_op)

    grover_rows = []
    population_matrix = []
    for marked_index, label in enumerate(COMPUTATIONAL_BASIS):
        result = run_grover_search(marked_index, epsilon=1.0)
        population_matrix.append(result.final_populations)
        grover_rows.append(
            {
                "marked_label": label,
                "marked_index": marked_index,
                "marked_population": result.marked_population,
                "deviation_fidelity": result.deviation_fidelity,
                "final_populations": [float(value) for value in result.final_populations],
            }
        )
    population_matrix_np = np.array(population_matrix, dtype=float)

    synthetic_epsilon = 0.08
    qst_marked_index = 2
    qst_target = run_grover_search(qst_marked_index, epsilon=synthetic_epsilon).final_state
    qst_rows = qst_noise_rows(
        config,
        qst_target,
        noise_levels=(0.0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.08),
        seeds=tuple(range(600, 640)),
    )

    epsilons = np.logspace(-6, 0, 180)
    figures = {
        "product_operator_decomposition": figure_dir / "product_operator_decomposition.png",
        "grover_marked_state_populations": figure_dir / "grover_marked_state_populations.png",
        "pseudopure_visibility": figure_dir / "pseudopure_visibility.png",
        "qst_noise_sensitivity": figure_dir / "qst_noise_sensitivity.png",
    }
    plot_product_operator_decomposition(figures["product_operator_decomposition"], iz_coeffs, q_coeffs)
    plot_grover_populations(figures["grover_marked_state_populations"], population_matrix_np)
    plot_pseudopure_visibility(figures["pseudopure_visibility"], epsilons)
    plot_qst_noise(figures["qst_noise_sensitivity"], qst_rows)

    iz_reconstruction = reconstruct_from_product_coefficients(iz_coeffs)
    q_reconstruction = reconstruct_from_product_coefficients(q_coeffs)
    iz_residual = float(np.linalg.norm(config.i_z - iz_reconstruction))
    q_residual = float(np.linalg.norm(q_op - q_reconstruction))

    synthetic_pps_result = run_grover_search(qst_marked_index, epsilon=synthetic_epsilon)
    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "spin32_quadrupolar_qip",
        "logical_encoding": {
            "basis_order": list(COMPUTATIONAL_BASIS),
            "spin_m_order": [float(value) for value in config.m_vals],
            "interpretation": "|m=3/2,1/2,-1/2,-3/2> mapped to |00>,|01>,|10>,|11>",
        },
        "product_operator_decomposition": {
            "iz_nonzero_coefficients": nonzero_coefficients(iz_coeffs),
            "quadrupolar_traceless_nonzero_coefficients": nonzero_coefficients(q_coeffs),
            "iz_reconstruction_residual": iz_residual,
            "quadrupolar_reconstruction_residual": q_residual,
        },
        "grover_ideal": {
            "marked_state_rows": grover_rows,
            "min_marked_population": float(min(row["marked_population"] for row in grover_rows)),
            "min_deviation_fidelity": float(min(row["deviation_fidelity"] for row in grover_rows)),
        },
        "pseudo_pure_signal": {
            "synthetic_epsilon": synthetic_epsilon,
            "marked_label": COMPUTATIONAL_BASIS[qst_marked_index],
            "marked_population": synthetic_pps_result.marked_population,
            "unmarked_population": float((1.0 - synthetic_epsilon) / 4.0),
            "deviation_contrast": synthetic_epsilon,
        },
        "qst_noise_sensitivity": qst_rows,
        "scientific_interpretation": {
            "captures": [
                "a spin-3/2 quadrupolar nucleus provides a four-level logical manifold equivalent to two qubits",
                "Iz decomposes as ZI + 0.5 IZ in the logical basis",
                "the first-order quadrupolar term decomposes as a logical ZZ interaction",
                "a two-qubit Grover step maps the uniform state to the marked pseudo-pure deviation density",
                "the existing seven-phase QST machinery can reconstruct the synthetic logical output",
            ],
            "does_not_capture": [
                "the full experimental pulse-compilation sequence from the review is not reproduced",
                "strongly modulating or GRAPE pulse optimization is not included in this reproduction",
                "relaxation during the algorithm is not included here; it remains covered by Papers A, C, and E",
                "real high-temperature NMR polarization is much smaller than the synthetic epsilon used for visible plots",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "logical_mapping": "|3/2>,|1/2>,|-1/2>,|-3/2> -> |00>,|01>,|10>,|11>",
            "pseudo_pure_state": "rho_pps = (1-epsilon) I/4 + epsilon |psi><psi|",
            "iz_logical_decomposition": "Iz = ZI + 0.5 IZ",
            "quadrupolar_logical_decomposition": "3 Iz^2 - I(I+1) I = 3 ZZ for I=3/2",
            "grover_oracle": "O_m = I - 2 |m><m|",
            "grover_diffusion": "D = 2 |s><s| - I",
            "grover_search": "rho_f = (D O_m HxH) rho_00 (D O_m HxH)^dagger",
            "qst": "signals from seven tomography rotations, then A vec(rho)=b",
        },
        "simulation_config": {
            "nmr_reference_config": {
                "i_spin": config.i_spin,
                "dim": config.dim,
                "nu_q_hz": config.nu_q,
                "m_vals": [float(value) for value in config.m_vals],
            },
            "synthetic_epsilon": synthetic_epsilon,
            "qst_marked_index": qst_marked_index,
            "qst_noise_seed_count": 40,
        },
        "assumptions": [
            "This reproduction targets the encoded-logical-processor structure of the review, not a digitized experimental figure.",
            "The computational basis follows the descending spin-projection order already used by the Na-23 code.",
            "The identity component of a pseudo-pure state is kept in density matrices but interpreted as NMR-silent.",
            "The algorithm benchmark is the minimal two-qubit Grover case because one Grover iteration is exact for N=4.",
            "Tomography noise is synthetic and relative to the simulated complex tomography amplitudes.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": {
            "iz_decomposition": nonzero_coefficients(iz_coeffs),
            "quadrupolar_decomposition": nonzero_coefficients(q_coeffs),
            "min_grover_marked_population": metrics["grover_ideal"]["min_marked_population"],
            "min_grover_deviation_fidelity": metrics["grover_ideal"]["min_deviation_fidelity"],
            "synthetic_pps_marked_population": metrics["pseudo_pure_signal"]["marked_population"],
            "qst_noise_0p02_deviation_fidelity_mean": next(
                row["deviation_fidelity_mean"]
                for row in qst_rows
                if abs(row["noise_std"] - 0.02) < 1e-15
            ),
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# Quantum Information Processing By NMR On Quadrupolar Nuclei",
                "",
                "This run implements the minimal logical-processor structure of a",
                "spin-3/2 quadrupolar nucleus: four spin levels are treated as two",
                "logical qubits.",
                "",
                "Key reproduced identities:",
                "",
                "- `Iz = ZI + 0.5 IZ` in the logical product-operator basis.",
                "- `3 Iz^2 - I(I+1) I = 3 ZZ` for `I=3/2`.",
                "- One two-qubit Grover iteration maps the uniform state to the",
                "  marked pseudo-pure deviation density.",
                "",
                f"Minimum ideal Grover marked-state population: `{metrics['grover_ideal']['min_marked_population']:.12g}`.",
                f"Minimum ideal Grover deviation fidelity: `{metrics['grover_ideal']['min_deviation_fidelity']:.12g}`.",
                f"Synthetic pseudo-pure marked population at epsilon={synthetic_epsilon}: `{synthetic_pps_result.marked_population:.12g}`.",
                "",
                "This is a platform-structure reproduction, not a full experimental",
                "pulse-sequence reproduction.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the quadrupolar-NMR QIP Paper G target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
