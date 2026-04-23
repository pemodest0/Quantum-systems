from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport import adjacency_for_topology, classify_transport_regime, simulate_transport, static_disorder_energies  # noqa: E402


@dataclass(frozen=True)
class BaseParameters:
    coupling_hz: float
    sink_rate_hz: float
    loss_rate_hz: float


def _load_config(path: Path) -> tuple[dict[str, object], np.ndarray, np.ndarray, BaseParameters]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    times = np.linspace(0.0, float(raw["time_grid"]["t_final"]), int(raw["time_grid"]["n_samples"]))
    dephasing_rates = np.asarray(raw["dephasing_rates_hz"], dtype=float)
    base = BaseParameters(
        coupling_hz=float(raw["base_parameters"]["coupling_hz"]),
        sink_rate_hz=float(raw["base_parameters"]["sink_rate_hz"]),
        loss_rate_hz=float(raw["base_parameters"]["loss_rate_hz"]),
    )
    return raw, times, dephasing_rates, base


def _mean_std(values: list[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 1:
        return float(arr[0]), 0.0
    return float(np.mean(arr)), float(np.std(arr, ddof=1))


def _initial_site_for_sink_sweep(topology: str, n_sites: int, trap_site: int) -> int:
    if topology == "chain":
        return 0 if trap_site >= n_sites // 2 else n_sites - 1
    if topology == "ring":
        return (trap_site + n_sites // 2) % n_sites
    return (trap_site + 1) % n_sites


def _ring_shortest_distance(n_sites: int, initial_site: int, trap_site: int) -> int:
    delta = abs(trap_site - initial_site)
    return int(min(delta, n_sites - delta))


def _ring_unique_distances(n_sites: int) -> list[int]:
    return list(range(1, (n_sites // 2) + 1))


def _graph_metrics(adjacency: np.ndarray, initial_site: int, trap_site: int) -> dict[str, float]:
    graph = nx.from_numpy_array(np.asarray(adjacency, dtype=float))
    degree_dict = dict(graph.degree())
    closeness_dict = nx.closeness_centrality(graph)
    shortest_paths = nx.shortest_path_length(graph, target=trap_site)
    shortest_paths_dict = {int(node): float(distance) for node, distance in shortest_paths.items()}
    mean_distance_to_trap = float(np.mean(list(shortest_paths_dict.values())))
    return {
        "trap_degree": float(degree_dict[trap_site]),
        "trap_closeness": float(closeness_dict[trap_site]),
        "mean_distance_to_trap": mean_distance_to_trap,
        "initial_to_trap_distance": float(shortest_paths_dict[initial_site]),
    }


def _pearson(x: list[float], y: list[float]) -> float:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size < 2 or np.allclose(x_arr, x_arr[0]) or np.allclose(y_arr, y_arr[0]):
        return float("nan")
    return float(np.corrcoef(x_arr, y_arr)[0, 1])


def _ensemble_scan(
    *,
    topology: str,
    n_sites: int,
    initial_site: int,
    trap_site: int,
    coupling_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
    disorder_strength_hz: float,
    seeds: tuple[int, ...],
    times: np.ndarray,
    dephasing_rates: np.ndarray,
) -> dict[str, object]:
    adjacency = adjacency_for_topology(topology, n_sites)

    rows: list[dict[str, object]] = []
    for rate in dephasing_rates:
        eta_values: list[float] = []
        purity_values: list[float] = []
        entropy_values: list[float] = []
        pop_entropy_values: list[float] = []
        pr_values: list[float] = []
        ipr_values: list[float] = []
        trace_values: list[float] = []
        closure_values: list[float] = []
        eig_values: list[float] = []
        for seed in seeds:
            site_energies = (
                np.zeros(n_sites, dtype=float)
                if disorder_strength_hz <= 0.0
                else static_disorder_energies(n_sites, disorder_strength_hz, seed)
            )
            result = simulate_transport(
                adjacency=adjacency,
                coupling_hz=coupling_hz,
                dephasing_rate_hz=float(rate),
                sink_rate_hz=sink_rate_hz,
                loss_rate_hz=loss_rate_hz,
                times=times,
                initial_site=initial_site,
                trap_site=trap_site,
                site_energies_hz=site_energies,
            )
            eta_values.append(result.transport_efficiency)
            purity_values.append(result.final_purity)
            entropy_values.append(result.final_entropy)
            pop_entropy_values.append(result.final_population_shannon_entropy)
            pr_values.append(result.final_participation_ratio)
            ipr_values.append(result.final_ipr)
            trace_values.append(result.max_trace_deviation)
            closure_values.append(result.max_population_closure_error)
            eig_values.append(result.min_state_eigenvalue)
        eta_mean, eta_std = _mean_std(eta_values)
        purity_mean, purity_std = _mean_std(purity_values)
        entropy_mean, entropy_std = _mean_std(entropy_values)
        pop_entropy_mean, pop_entropy_std = _mean_std(pop_entropy_values)
        pr_mean, pr_std = _mean_std(pr_values)
        ipr_mean, ipr_std = _mean_std(ipr_values)
        rows.append(
            {
                "gamma_phi_hz": float(rate),
                "eta_mean": eta_mean,
                "eta_std": eta_std,
                "purity_mean": purity_mean,
                "purity_std": purity_std,
                "entropy_mean": entropy_mean,
                "entropy_std": entropy_std,
                "population_entropy_mean": pop_entropy_mean,
                "population_entropy_std": pop_entropy_std,
                "participation_ratio_mean": pr_mean,
                "participation_ratio_std": pr_std,
                "ipr_mean": ipr_mean,
                "ipr_std": ipr_std,
                "trace_diag_max": float(np.max(trace_values)),
                "closure_diag_max": float(np.max(closure_values)),
                "min_eig_min": float(np.min(eig_values)),
            }
        )

    eta_curve = np.array([row["eta_mean"] for row in rows], dtype=float)
    best_idx = int(np.argmax(eta_curve))
    best = rows[best_idx]
    metrics = _graph_metrics(adjacency, initial_site, trap_site)
    return {
        "topology": topology,
        "n_sites": n_sites,
        "initial_site": initial_site,
        "trap_site": trap_site,
        "disorder_strength_hz": disorder_strength_hz,
        "graph_metrics": metrics,
        "n_realizations": len(seeds),
        "rows": rows,
        "best_idx": best_idx,
        "best_regime": classify_transport_regime(best_idx, len(dephasing_rates)),
        "eta_best_mean": float(best["eta_mean"]),
        "eta_best_std": float(best["eta_std"]),
        "gamma_phi_best": float(best["gamma_phi_hz"]),
        "final_purity_mean": float(best["purity_mean"]),
        "final_entropy_mean": float(best["entropy_mean"]),
        "final_population_entropy_mean": float(best["population_entropy_mean"]),
        "final_participation_ratio_mean": float(best["participation_ratio_mean"]),
        "final_ipr_mean": float(best["ipr_mean"]),
        "trace_diag_best": float(best["trace_diag_max"]),
        "closure_diag_best": float(best["closure_diag_max"]),
        "min_eig_best": float(best["min_eig_min"]),
    }


def _plot_with_band(path: Path, x: np.ndarray, y: np.ndarray, std: np.ndarray, *, title: str, xlabel: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.plot(x, y, marker="o", lw=1.8)
    if np.any(std > 0.0):
        ax.fill_between(x, y - std, y + std, alpha=0.18)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_chain_crossover(path: Path, results: list[dict[str, object]]) -> None:
    x = np.array([row["w_over_j"] for row in results], dtype=float)
    eta = np.array([row["eta_best_mean"] for row in results], dtype=float)
    eta_std = np.array([row["eta_best_std"] for row in results], dtype=float)
    gamma = np.array([row["gamma_phi_best"] for row in results], dtype=float)
    purity = np.array([row["final_purity_mean"] for row in results], dtype=float)
    entropy = np.array([row["final_entropy_mean"] for row in results], dtype=float)
    pr = np.array([row["final_participation_ratio_mean"] for row in results], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.2), sharex=True)
    axes[0, 0].plot(x, eta, marker="o", lw=1.8)
    axes[0, 0].fill_between(x, eta - eta_std, eta + eta_std, alpha=0.16)
    axes[0, 0].set_ylabel(r"$\eta_{\mathrm{best}}$")
    axes[0, 0].set_title("Chain crossover: best sink efficiency")
    axes[0, 1].plot(x, gamma, marker="o", lw=1.8, color="#b45309")
    axes[0, 1].set_ylabel(r"$\gamma_\phi^{\mathrm{best}}$")
    axes[0, 1].set_title("Chain crossover: optimal dephasing")
    axes[1, 0].plot(x, purity, marker="o", lw=1.8, color="#0f766e", label="purity")
    axes[1, 0].plot(x, entropy, marker="s", lw=1.6, color="#7c3aed", label="entropy")
    axes[1, 0].set_ylabel("Conditional state metrics")
    axes[1, 0].set_title("Chain crossover: final conditional purity and entropy")
    axes[1, 0].legend(frameon=False)
    axes[1, 1].plot(x, pr, marker="o", lw=1.8, color="#2563eb")
    axes[1, 1].set_ylabel("Participation ratio")
    axes[1, 1].set_title("Chain crossover: final normalized participation ratio")
    for ax in axes[1, :]:
        ax.set_xlabel(r"$W/J$")
    for ax in axes.ravel():
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_ring_size(path: Path, results: list[dict[str, object]]) -> None:
    x = np.array([row["n_sites"] for row in results], dtype=float)
    eta = np.array([row["eta_best_mean"] for row in results], dtype=float)
    gamma = np.array([row["gamma_phi_best"] for row in results], dtype=float)
    purity = np.array([row["final_purity_mean"] for row in results], dtype=float)
    pr = np.array([row["final_participation_ratio_mean"] for row in results], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.2), sharex=True)
    axes[0, 0].plot(x, eta, marker="o", lw=1.8)
    axes[0, 0].set_ylabel(r"$\eta_{\mathrm{best}}$")
    axes[0, 0].set_title("Ring size sweep: best sink efficiency")
    axes[0, 1].plot(x, gamma, marker="o", lw=1.8, color="#b45309")
    axes[0, 1].set_ylabel(r"$\gamma_\phi^{\mathrm{best}}$")
    axes[0, 1].set_title("Ring size sweep: optimal dephasing")
    axes[1, 0].plot(x, purity, marker="o", lw=1.8, color="#0f766e")
    axes[1, 0].set_ylabel("Final purity")
    axes[1, 0].set_title("Ring size sweep: final conditional purity")
    axes[1, 1].plot(x, pr, marker="o", lw=1.8, color="#2563eb")
    axes[1, 1].set_ylabel("Participation ratio")
    axes[1, 1].set_title("Ring size sweep: final normalized participation ratio")
    for ax in axes[1, :]:
        ax.set_xlabel("Number of sites N")
    for ax in axes.ravel():
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_ring_parity_distance(path: Path, results: list[dict[str, object]]) -> None:
    n_values = sorted({int(row["n_sites"]) for row in results})
    distance_values = sorted({int(row["ring_shortest_distance"]) for row in results})
    eta_matrix = np.full((len(n_values), len(distance_values)), np.nan, dtype=float)
    gamma_matrix = np.full_like(eta_matrix, np.nan)

    n_to_idx = {value: idx for idx, value in enumerate(n_values)}
    d_to_idx = {value: idx for idx, value in enumerate(distance_values)}
    for row in results:
        i = n_to_idx[int(row["n_sites"])]
        j = d_to_idx[int(row["ring_shortest_distance"])]
        eta_matrix[i, j] = float(row["eta_best_mean"])
        gamma_matrix[i, j] = float(row["gamma_phi_best"])

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.6))

    for ax, matrix, title, label in (
        (axes[0, 0], eta_matrix, "Ring parity-distance study: best sink efficiency", r"$\eta_{\mathrm{best}}$"),
        (axes[0, 1], gamma_matrix, "Ring parity-distance study: optimal dephasing", r"$\gamma_\phi^{\mathrm{best}}$"),
    ):
        image = ax.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap="viridis")
        ax.set_xticks(np.arange(len(distance_values)), labels=[str(d) for d in distance_values])
        ax.set_yticks(np.arange(len(n_values)), labels=[str(n) for n in n_values])
        ax.set_xlabel("Shortest ring distance to trap")
        ax.set_ylabel("Ring size N")
        ax.set_title(title)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if np.isfinite(matrix[i, j]):
                    ax.text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center", fontsize=8, color="white")
        fig.colorbar(image, ax=ax, label=label)

    parity_styles = {
        "even": ("#2563eb", "o"),
        "odd": ("#dc2626", "s"),
    }
    for parity, (color, marker) in parity_styles.items():
        parity_rows = [row for row in results if row["ring_parity"] == parity]
        axes[1, 0].scatter(
            [int(row["ring_shortest_distance"]) for row in parity_rows],
            [float(row["eta_best_mean"]) for row in parity_rows],
            color=color,
            marker=marker,
            s=60,
            alpha=0.85,
            label=f"{parity} N",
        )
        axes[1, 1].scatter(
            [int(row["ring_shortest_distance"]) for row in parity_rows],
            [float(row["gamma_phi_best"]) for row in parity_rows],
            color=color,
            marker=marker,
            s=60,
            alpha=0.85,
            label=f"{parity} N",
        )
    axes[1, 0].set_title("Best sink efficiency at matched shortest-path distance")
    axes[1, 0].set_xlabel("Shortest ring distance to trap")
    axes[1, 0].set_ylabel(r"$\eta_{\mathrm{best}}$")
    axes[1, 1].set_title("Optimal dephasing at matched shortest-path distance")
    axes[1, 1].set_xlabel("Shortest ring distance to trap")
    axes[1, 1].set_ylabel(r"$\gamma_\phi^{\mathrm{best}}$")
    axes[1, 0].legend(frameon=False)
    axes[1, 1].legend(frameon=False)
    for ax in axes[1, :]:
        ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _heatmap(path: Path, matrix: np.ndarray, x_labels: list[str], y_labels: list[str], *, title: str, cbar_label: str, fmt: str = ".3f") -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    image = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_xticks(np.arange(len(x_labels)), labels=x_labels)
    ax.set_yticks(np.arange(len(y_labels)), labels=y_labels)
    ax.set_title(title)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, format(matrix[i, j], fmt), ha="center", va="center", fontsize=8, color="white")
    fig.colorbar(image, ax=ax, label=cbar_label)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_metric_correlation(path: Path, sink_results: dict[str, list[dict[str, object]]]) -> dict[str, float]:
    metric_names = [
        ("trap_degree", "Trap degree"),
        ("trap_closeness", "Trap closeness"),
        ("mean_distance_to_trap", "Mean distance to trap"),
        ("initial_to_trap_distance", "Initial-to-trap distance"),
    ]
    topology_colors = {"chain": "#2563eb", "ring": "#059669", "complete": "#dc2626"}
    all_rows = [
        (topology, row)
        for topology, rows in sink_results.items()
        for row in rows
    ]
    eta_values = [float(row["eta_best_mean"]) for _, row in all_rows]

    correlations: dict[str, float] = {}
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.4))
    for ax, (metric_key, label) in zip(axes.ravel(), metric_names, strict=True):
        metric_values = [float(row["graph_metrics"][metric_key]) for _, row in all_rows]
        correlations[metric_key] = _pearson(metric_values, eta_values)
        for topology, row in all_rows:
            ax.scatter(
                float(row["graph_metrics"][metric_key]),
                float(row["eta_best_mean"]),
                s=55,
                alpha=0.85,
                color=topology_colors[topology],
                label=topology if topology not in ax.get_legend_handles_labels()[1] else None,
            )
        ax.set_title(f"{label} vs best sink efficiency\nPearson r = {correlations[metric_key]:.3f}")
        ax.set_xlabel(label)
        ax.set_ylabel(r"$\eta_{\mathrm{best}}$")
        ax.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return correlations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run refined transport studies for crossover, ring scaling, and sink placement.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_targeted_studies_config.json"),
        help="Path to the targeted studies configuration file.",
    )
    parser.add_argument(
        "--only",
        choices=("all", "chain", "ring", "ring-parity", "sink"),
        default="all",
        help="Run only one targeted sub-study and merge it into the existing results file.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    raw, times, dephasing_rates, base = _load_config(config_path)

    output_dir = ROOT / "outputs" / "transport_networks" / str(raw["output_subdir"]) / "latest"
    figure_dir = output_dir / "figures"
    results_path = output_dir / "results.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    if results_path.exists():
        results_payload: dict[str, object] = json.loads(results_path.read_text(encoding="utf-8"))
    else:
        results_payload = {"study_name": raw["study_name"]}
    csv_rows: list[dict[str, object]] = []

    # Chain crossover refinement
    if args.only in ("all", "chain"):
        chain_cfg = raw["chain_crossover"]
        chain_rates = np.asarray(chain_cfg.get("dephasing_rates_hz", raw["dephasing_rates_hz"]), dtype=float)
        chain_results: list[dict[str, object]] = []
        for value in chain_cfg["w_over_j_values"]:
            print(f"[chain] running W/J={value}", flush=True)
            result = _ensemble_scan(
                topology="chain",
                n_sites=int(chain_cfg["n_sites"]),
                initial_site=int(chain_cfg["initial_site"]),
                trap_site=int(chain_cfg["trap_site"]),
                coupling_hz=base.coupling_hz,
                sink_rate_hz=base.sink_rate_hz,
                loss_rate_hz=base.loss_rate_hz,
                disorder_strength_hz=float(value) * base.coupling_hz,
                seeds=tuple(int(seed) for seed in chain_cfg["seeds"]),
                times=times,
                dephasing_rates=chain_rates,
            )
            result["w_over_j"] = float(value)
            chain_results.append(result)
            csv_rows.append(
                {
                    "study": "chain_crossover",
                    "x_value": float(value),
                    "topology": "chain",
                    "trap_site": int(chain_cfg["trap_site"]),
                    "n_sites": int(chain_cfg["n_sites"]),
                    "best_regime": result["best_regime"],
                    "eta_best_mean": result["eta_best_mean"],
                    "eta_best_std": result["eta_best_std"],
                    "gamma_phi_best": result["gamma_phi_best"],
                    "final_purity_mean": result["final_purity_mean"],
                    "final_entropy_mean": result["final_entropy_mean"],
                    "final_population_entropy_mean": result["final_population_entropy_mean"],
                    "final_participation_ratio_mean": result["final_participation_ratio_mean"],
                    "final_ipr_mean": result["final_ipr_mean"],
                    "n_realizations": result["n_realizations"],
                }
            )
        results_payload["chain_crossover"] = {"results": chain_results}
        _plot_chain_crossover(figure_dir / "chain_crossover_refined.png", chain_results)
        results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    # Refined ring-size sweep
    if args.only in ("all", "ring"):
        ring_cfg = raw["ring_size_refined"]
        ring_results: list[dict[str, object]] = []
        for n_sites in ring_cfg["n_values"]:
            print(f"[ring] running N={n_sites}", flush=True)
            result = _ensemble_scan(
                topology="ring",
                n_sites=int(n_sites),
                initial_site=int(int(n_sites) // 2),
                trap_site=0,
                coupling_hz=base.coupling_hz,
                sink_rate_hz=base.sink_rate_hz,
                loss_rate_hz=base.loss_rate_hz,
                disorder_strength_hz=0.0,
                seeds=(1,),
                times=times,
                dephasing_rates=dephasing_rates,
            )
            ring_results.append(result)
            csv_rows.append(
                {
                    "study": "ring_size_refined",
                    "x_value": int(n_sites),
                    "topology": "ring",
                    "trap_site": 0,
                    "n_sites": int(n_sites),
                    "best_regime": result["best_regime"],
                    "eta_best_mean": result["eta_best_mean"],
                    "eta_best_std": result["eta_best_std"],
                    "gamma_phi_best": result["gamma_phi_best"],
                    "final_purity_mean": result["final_purity_mean"],
                    "final_entropy_mean": result["final_entropy_mean"],
                    "final_population_entropy_mean": result["final_population_entropy_mean"],
                    "final_participation_ratio_mean": result["final_participation_ratio_mean"],
                    "final_ipr_mean": result["final_ipr_mean"],
                    "n_realizations": result["n_realizations"],
                }
            )
        results_payload["ring_size_refined"] = {"results": ring_results}
        _plot_ring_size(figure_dir / "ring_size_refined.png", ring_results)
        results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    # Ring parity versus sink distance
    if args.only in ("all", "ring-parity"):
        ring_cfg = raw["ring_parity_distance"]
        ring_distance_rates = np.asarray(ring_cfg.get("dephasing_rates_hz", raw["dephasing_rates_hz"]), dtype=float)
        parity_distance_results: list[dict[str, object]] = []
        for n_sites in ring_cfg["n_values"]:
            initial_site = int(ring_cfg.get("initial_site", 0))
            for distance in _ring_unique_distances(int(n_sites)):
                trap_site = (initial_site + int(distance)) % int(n_sites)
                print(
                    f"[ring-parity] running N={n_sites}, shortest_distance={distance}, trap_site={trap_site}",
                    flush=True,
                )
                result = _ensemble_scan(
                    topology="ring",
                    n_sites=int(n_sites),
                    initial_site=initial_site,
                    trap_site=trap_site,
                    coupling_hz=base.coupling_hz,
                    sink_rate_hz=base.sink_rate_hz,
                    loss_rate_hz=base.loss_rate_hz,
                    disorder_strength_hz=float(ring_cfg.get("disorder_strength_hz", 0.0)),
                    seeds=(1,),
                    times=times,
                    dephasing_rates=ring_distance_rates,
                )
                result["ring_shortest_distance"] = int(distance)
                result["ring_parity"] = "even" if int(n_sites) % 2 == 0 else "odd"
                parity_distance_results.append(result)
                csv_rows.append(
                    {
                        "study": "ring_parity_distance",
                        "x_value": int(distance),
                        "topology": "ring",
                        "trap_site": trap_site,
                        "n_sites": int(n_sites),
                        "ring_parity": result["ring_parity"],
                        "ring_shortest_distance": int(distance),
                        "best_regime": result["best_regime"],
                        "eta_best_mean": result["eta_best_mean"],
                        "eta_best_std": result["eta_best_std"],
                        "gamma_phi_best": result["gamma_phi_best"],
                        "final_purity_mean": result["final_purity_mean"],
                        "final_entropy_mean": result["final_entropy_mean"],
                        "final_population_entropy_mean": result["final_population_entropy_mean"],
                        "final_participation_ratio_mean": result["final_participation_ratio_mean"],
                        "final_ipr_mean": result["final_ipr_mean"],
                        "n_realizations": result["n_realizations"],
                    }
                )

        distance_summary: dict[str, dict[str, float]] = {}
        common_distances = sorted({int(row["ring_shortest_distance"]) for row in parity_distance_results})
        for distance in common_distances:
            even_rows = [row for row in parity_distance_results if row["ring_shortest_distance"] == distance and row["ring_parity"] == "even"]
            odd_rows = [row for row in parity_distance_results if row["ring_shortest_distance"] == distance and row["ring_parity"] == "odd"]
            if even_rows and odd_rows:
                even_eta = float(np.mean([row["eta_best_mean"] for row in even_rows]))
                odd_eta = float(np.mean([row["eta_best_mean"] for row in odd_rows]))
                even_gamma = float(np.mean([row["gamma_phi_best"] for row in even_rows]))
                odd_gamma = float(np.mean([row["gamma_phi_best"] for row in odd_rows]))
                distance_summary[str(distance)] = {
                    "even_eta_mean": even_eta,
                    "odd_eta_mean": odd_eta,
                    "eta_even_minus_odd": even_eta - odd_eta,
                    "even_gamma_mean": even_gamma,
                    "odd_gamma_mean": odd_gamma,
                    "gamma_even_minus_odd": even_gamma - odd_gamma,
                }

        results_payload["ring_parity_distance"] = {
            "results": parity_distance_results,
            "distance_summary": distance_summary,
        }
        _plot_ring_parity_distance(figure_dir / "ring_parity_distance.png", parity_distance_results)
        results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    # Sink-position sweep
    if args.only in ("all", "sink"):
        sink_cfg = raw["sink_position_sweep"]
        sink_results: dict[str, list[dict[str, object]]] = {}
        topology_labels = list(sink_cfg["topologies"])
        trap_labels = [str(index) for index in range(int(sink_cfg["n_sites"]))]
        eta_matrix = np.zeros((len(topology_labels), len(trap_labels)), dtype=float)
        gamma_matrix = np.zeros_like(eta_matrix)
        entropy_matrix = np.zeros_like(eta_matrix)
        pr_matrix = np.zeros_like(eta_matrix)

        for topo_idx, topology in enumerate(topology_labels):
            sink_results[topology] = []
            for trap_site in range(int(sink_cfg["n_sites"])):
                print(f"[sink] running topology={topology}, trap_site={trap_site}", flush=True)
                result = _ensemble_scan(
                    topology=topology,
                    n_sites=int(sink_cfg["n_sites"]),
                    initial_site=_initial_site_for_sink_sweep(topology, int(sink_cfg["n_sites"]), trap_site),
                    trap_site=trap_site,
                    coupling_hz=base.coupling_hz,
                    sink_rate_hz=base.sink_rate_hz,
                    loss_rate_hz=base.loss_rate_hz,
                    disorder_strength_hz=float(sink_cfg["disorder_strength_hz"]),
                    seeds=tuple(int(seed) for seed in sink_cfg["seeds"]),
                    times=times,
                    dephasing_rates=dephasing_rates,
                )
                sink_results[topology].append(result)
                eta_matrix[topo_idx, trap_site] = result["eta_best_mean"]
                gamma_matrix[topo_idx, trap_site] = result["gamma_phi_best"]
                entropy_matrix[topo_idx, trap_site] = result["final_entropy_mean"]
                pr_matrix[topo_idx, trap_site] = result["final_participation_ratio_mean"]
                csv_rows.append(
                    {
                        "study": "sink_position_sweep",
                        "x_value": trap_site,
                        "topology": topology,
                        "trap_site": trap_site,
                        "n_sites": int(sink_cfg["n_sites"]),
                        "best_regime": result["best_regime"],
                        "eta_best_mean": result["eta_best_mean"],
                        "eta_best_std": result["eta_best_std"],
                        "gamma_phi_best": result["gamma_phi_best"],
                        "trap_degree": result["graph_metrics"]["trap_degree"],
                        "trap_closeness": result["graph_metrics"]["trap_closeness"],
                        "mean_distance_to_trap": result["graph_metrics"]["mean_distance_to_trap"],
                        "initial_to_trap_distance": result["graph_metrics"]["initial_to_trap_distance"],
                        "final_purity_mean": result["final_purity_mean"],
                        "final_entropy_mean": result["final_entropy_mean"],
                        "final_population_entropy_mean": result["final_population_entropy_mean"],
                        "final_participation_ratio_mean": result["final_participation_ratio_mean"],
                        "final_ipr_mean": result["final_ipr_mean"],
                        "n_realizations": result["n_realizations"],
                    }
                )

        results_payload["sink_position_sweep"] = sink_results
        results_payload["sink_position_metric_correlations"] = _plot_metric_correlation(
            figure_dir / "sink_position_metric_correlations.png",
            sink_results,
        )
        _heatmap(
            figure_dir / "sink_position_eta_heatmap.png",
            eta_matrix,
            x_labels=trap_labels,
            y_labels=topology_labels,
            title="Sink-position sweep: best sink efficiency",
            cbar_label=r"$\eta_{\mathrm{best}}$",
        )
        _heatmap(
            figure_dir / "sink_position_gamma_heatmap.png",
            gamma_matrix,
            x_labels=trap_labels,
            y_labels=topology_labels,
            title="Sink-position sweep: optimal dephasing",
            cbar_label=r"$\gamma_\phi^{\mathrm{best}}$",
        )
        _heatmap(
            figure_dir / "sink_position_entropy_heatmap.png",
            entropy_matrix,
            x_labels=trap_labels,
            y_labels=topology_labels,
            title="Sink-position sweep: final conditional entropy",
            cbar_label=r"$S(\rho_{\mathrm{net}})$",
        )
        _heatmap(
            figure_dir / "sink_position_participation_heatmap.png",
            pr_matrix,
            x_labels=trap_labels,
            y_labels=topology_labels,
            title="Sink-position sweep: final participation ratio",
            cbar_label="PR",
        )
        results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    if csv_rows:
        csv_path = output_dir / f"targeted_studies_table_{args.only}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)

    results_path.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "script": "scripts/run_transport_targeted_studies.py",
                "config_path": str(config_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
