from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import (  # noqa: E402
    generate_network_instance,
    graph_from_adjacency,
    mean_std_sem_ci95,
    simulate_classical_transport,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
)
from scripts.run_transport_methodological_benchmarks import _weighted_instance  # noqa: E402


TARGET_FAMILIES = ("ring", "chain", "square_lattice_2d", "modular_two_community", "random_geometric")
FRACTAL_FAMILIES = ("sierpinski_gasket", "sierpinski_carpet_like", "square_lattice_2d")
MATERIAL_ROWS = [
    {
        "motivation": "Photosynthetic excitation transfer",
        "real_system": "Chromophores with electronic excitation transfer",
        "what_we_model": "A single excitation moving on an effective graph with coherence and dephasing.",
        "what_we_do_not_claim": "No microscopic FMO Hamiltonian or spectroscopy reproduction.",
        "anchor": "Engel 2007; Mohseni 2008; Rebentrost 2009",
    },
    {
        "motivation": "Perovskite nanocrystal superlattices",
        "real_system": "Exciton propagation with disorder and environmental fluctuations",
        "what_we_model": "Balanced disorder and phase scrambling in finite networks.",
        "what_we_do_not_claim": "No nanocrystal geometry, temperature-dependent material constants, or imaging model.",
        "anchor": "Blach 2025",
    },
    {
        "motivation": "Superconducting / qubit simulators",
        "real_system": "Programmable finite networks with tunable coupling and dissipation",
        "what_we_model": "Finite graph transport with target channel, loss and dephasing.",
        "what_we_do_not_claim": "No hardware pulse calibration or device-specific noise spectroscopy.",
        "anchor": "Maier 2019",
    },
]


def profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": "smoke",
            "n_sites_values": [8],
            "graph_realizations": 1,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "disorder_seeds": [3],
            "dephasing_over_coupling": [0.0, 0.6],
            "target_styles": ["near", "far"],
            "fractal_n_sites_values": [8],
            "t_final": 7.0,
            "n_time_samples": 56,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "graph_seed_base": 8100,
        }
    if profile == "interactive":
        return {
            "profile": "interactive",
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 2,
            "disorder_strength_over_coupling": [0.0, 0.4, 0.8],
            "disorder_seeds": [3, 5],
            "dephasing_over_coupling": [0.0, 0.2, 0.8, 1.4],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "fractal_n_sites_values": [8, 13, 20],
            "t_final": 10.0,
            "n_time_samples": 80,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "graph_seed_base": 8200,
        }
    if profile == "paper":
        return {
            "profile": "paper",
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 4,
            "disorder_strength_over_coupling": [0.0, 0.3, 0.6, 0.9],
            "disorder_seeds": [3, 5, 7, 11],
            "dephasing_over_coupling": [0.0, 0.1, 0.4, 0.8, 1.4],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "fractal_n_sites_values": [8, 13, 20],
            "t_final": 12.0,
            "n_time_samples": 100,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "graph_seed_base": 8300,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown_table(rows: list[dict[str, str]], path: Path) -> None:
    headers = ["motivation", "real_system", "what_we_model", "what_we_do_not_claim", "anchor"]
    labels = ["Motivation", "Real system", "What our model simulates", "What we do not claim", "Paper anchor"]
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for key in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _classification_snapshot() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "network_classification_complete" / "latest" / "metrics.json"
    if not path.exists():
        return {
            "available": False,
            "dynamic_accuracy": 0.0,
            "topology_accuracy": 0.0,
            "classical_accuracy": 0.0,
            "combined_accuracy": 0.0,
            "combined_baseline": 0.0,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"available": True, **payload}


def _target_rows(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, float]]:
    rows: list[dict[str, object]] = []
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    coupling = float(config["coupling_hz"])
    random_families = {"modular_two_community", "random_geometric"}

    for family in TARGET_FAMILIES:
        for n_sites in list(config["n_sites_values"]):
            realization_count = int(config["graph_realizations"]) if family in random_families else 1
            for realization in range(realization_count):
                graph_seed = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * realization + len(rows)
                if family not in random_families:
                    graph_seed = int(config["graph_seed_base"]) + int(n_sites) + realization
                base = generate_network_instance(family, n_sites=int(n_sites), seed=graph_seed, realization_index=realization)
                instance = _weighted_instance(base, "unweighted")
                initial_site = int(n_sites) - 1
                candidates = target_candidates(instance, initial_site=initial_site)
                for target_style in list(config["target_styles"]):
                    if target_style not in candidates:
                        continue
                    trap_site = int(candidates[target_style])
                    topo = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
                    for disorder in list(config["disorder_strength_over_coupling"]):
                        for disorder_seed in list(config["disorder_seeds"]):
                            seed = int(disorder_seed) + 17 * graph_seed + int(round(1000 * float(disorder)))
                            site_energies = static_disorder_energies(int(n_sites), float(disorder) * coupling, seed=seed)
                            zero_arrival = None
                            best: dict[str, object] | None = None
                            for gamma in list(config["dephasing_over_coupling"]):
                                result = simulate_transport(
                                    adjacency=instance.adjacency,
                                    coupling_hz=coupling,
                                    dephasing_rate_hz=float(gamma) * coupling,
                                    sink_rate_hz=float(config["sink_rate_hz"]),
                                    loss_rate_hz=float(config["loss_rate_hz"]),
                                    times=times,
                                    initial_site=initial_site,
                                    trap_site=trap_site,
                                    site_energies_hz=site_energies,
                                    node_coordinates=instance.coordinates,
                                    sink_hit_threshold=0.1,
                                    transfer_threshold=0.5,
                                )
                                if abs(float(gamma)) < 1e-12:
                                    zero_arrival = float(result.transport_efficiency)
                                candidate = {
                                    "family": family,
                                    "n_sites": int(n_sites),
                                    "instance_id": instance.instance_id,
                                    "graph_seed": graph_seed,
                                    "realization": realization,
                                    "disorder_seed": int(disorder_seed),
                                    "disorder_strength_over_coupling": float(disorder),
                                    "target_style": target_style,
                                    "initial_site": initial_site,
                                    "trap_site": trap_site,
                                    "dephasing_over_coupling": float(gamma),
                                    "arrival": float(result.transport_efficiency),
                                    "sink_hitting_time_filled": float(result.times[-1]) if result.sink_hitting_time is None else float(result.sink_hitting_time),
                                    "loss_population": float(result.loss_population[-1]),
                                    "network_population": float(result.network_population[-1]),
                                    "mean_coherence_l1": float(result.mean_coherence_l1),
                                    "final_entropy": float(result.final_entropy),
                                    "participation_ratio": float(result.final_participation_ratio),
                                    "max_trace_deviation": float(result.max_trace_deviation),
                                    "max_population_closure_error": float(result.max_population_closure_error),
                                    "min_state_eigenvalue": float(result.min_state_eigenvalue),
                                }
                                candidate.update({f"topology_{key}": float(value) for key, value in topo.items()})
                                if best is None or float(candidate["arrival"]) > float(best["arrival"]):
                                    best = candidate
                                validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(result.max_trace_deviation))
                                validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(result.max_population_closure_error))
                                validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(result.min_state_eigenvalue))
                            if best is not None:
                                best["zero_dephasing_arrival"] = float(zero_arrival if zero_arrival is not None else best["arrival"])
                                best["dephasing_gain"] = float(best["arrival"]) - float(best["zero_dephasing_arrival"])
                                rows.append(best)
    return rows, validation


def _target_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["family"]), str(row["target_style"]))].append(row)
    out: list[dict[str, object]] = []
    for (family, target_style), items in sorted(grouped.items()):
        arrival = mean_std_sem_ci95(float(item["arrival"]) for item in items)
        gain = mean_std_sem_ci95(float(item["dephasing_gain"]) for item in items)
        out.append(
            {
                "family": family,
                "target_style": target_style,
                "n": arrival["n"],
                "arrival_mean": arrival["mean"],
                "arrival_ci95_low": arrival["ci95_low"],
                "arrival_ci95_high": arrival["ci95_high"],
                "dephasing_gain_mean": gain["mean"],
                "target_degree_mean": float(np.mean([float(item["topology_target_degree"]) for item in items])),
                "initial_target_distance_mean": float(np.mean([float(item["topology_initial_target_distance"]) for item in items])),
                "target_closeness_mean": float(np.mean([float(item["topology_target_closeness"]) for item in items])),
            }
        )
    return out


def _target_effect(rows: list[dict[str, object]]) -> dict[str, object]:
    by_context: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_context[
            (
                str(row["family"]),
                str(row["n_sites"]),
                str(row["graph_seed"]),
                str(row["disorder_strength_over_coupling"]),
            )
        ].append(row)
    spreads = []
    degree_spreads = []
    for items in by_context.values():
        if len({str(item["target_style"]) for item in items}) < 2:
            continue
        spreads.append(max(float(item["arrival"]) for item in items) - min(float(item["arrival"]) for item in items))
        degree_spreads.append(max(float(item["topology_target_degree"]) for item in items) - min(float(item["topology_target_degree"]) for item in items))
    degree_values = np.asarray([float(row["topology_target_degree"]) for row in rows], dtype=float)
    arrivals = np.asarray([float(row["arrival"]) for row in rows], dtype=float)
    degree_r2 = 1.0
    if degree_values.size > 2 and np.std(degree_values) > 1e-12 and np.std(arrivals) > 1e-12:
        degree_r2 = float(np.corrcoef(degree_values, arrivals)[0, 1] ** 2)
    spread_summary = mean_std_sem_ci95(spreads)
    return {
        "target_spread_mean": spread_summary["mean"],
        "target_spread_ci95_low": spread_summary["ci95_low"],
        "target_spread_ci95_high": spread_summary["ci95_high"],
        "max_target_spread": float(max(spreads, default=0.0)),
        "mean_target_degree_spread": float(np.mean(degree_spreads)) if degree_spreads else 0.0,
        "target_degree_arrival_r2": degree_r2,
        "strong_target_effect": bool(float(spread_summary["ci95_low"]) > 0.05),
    }


def _quantum_classical_rows(target_rows: list[dict[str, object]], config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, float]]:
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    max_closure = 0.0
    rows: list[dict[str, object]] = []
    cache: dict[tuple[object, ...], object] = {}
    for row in target_rows:
        key = (row["family"], row["n_sites"], row["graph_seed"], row["trap_site"])
        if key not in cache:
            instance = _weighted_instance(
                generate_network_instance(str(row["family"]), n_sites=int(row["n_sites"]), seed=int(row["graph_seed"]), realization_index=int(row["realization"])),
                "unweighted",
            )
            cache[key] = simulate_classical_transport(
                instance.adjacency,
                hopping_rate_hz=float(config["coupling_hz"]),
                sink_rate_hz=float(config["sink_rate_hz"]),
                loss_rate_hz=float(config["loss_rate_hz"]),
                times=times,
                initial_site=int(row["initial_site"]),
                trap_site=int(row["trap_site"]),
                sink_hit_threshold=0.1,
                transfer_threshold=0.5,
            )
        classical = cache[key]
        max_closure = max(max_closure, float(classical.max_population_closure_error))
        delta = float(row["arrival"]) - float(classical.transport_efficiency)
        if float(row["arrival"]) < 0.1 and float(classical.transport_efficiency) < 0.1:
            label = "both_poor"
        elif delta > 0.05:
            label = "quantum_advantage_like"
        elif abs(delta) <= 0.05:
            label = "classical_explains"
        else:
            label = "inconclusive"
        rows.append(
            {
                "family": row["family"],
                "n_sites": row["n_sites"],
                "target_style": row["target_style"],
                "disorder_strength_over_coupling": row["disorder_strength_over_coupling"],
                "dephasing_over_coupling": row["dephasing_over_coupling"],
                "arrival_quantum": row["arrival"],
                "arrival_classical": float(classical.transport_efficiency),
                "arrival_delta_quantum_minus_classical": delta,
                "quantum_hitting_time": row["sink_hitting_time_filled"],
                "classical_hitting_time": float(times[-1]) if classical.sink_hitting_time is None else float(classical.sink_hitting_time),
                "quantum_loss": row["loss_population"],
                "classical_loss": float(classical.loss_population[-1]),
                "comparison_label": label,
            }
        )
    return rows, {"classical_max_population_closure_error": max_closure}


def _fractal_rows(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, float], dict[str, dict[str, object]]]:
    rows: list[dict[str, object]] = []
    series: dict[str, dict[str, object]] = {}
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    for family in FRACTAL_FAMILIES:
        for n_sites in list(config["fractal_n_sites_values"]):
            seed = int(config["graph_seed_base"]) + int(n_sites) + len(rows)
            instance = generate_network_instance(family, n_sites=int(n_sites), seed=seed)
            initial_site = int(n_sites) - 1
            trap_site = int(target_candidates(instance, initial_site=initial_site)["far"])
            result = simulate_transport(
                adjacency=instance.adjacency,
                coupling_hz=float(config["coupling_hz"]),
                dephasing_rate_hz=0.0,
                sink_rate_hz=float(config["sink_rate_hz"]),
                loss_rate_hz=float(config["loss_rate_hz"]),
                times=times,
                initial_site=initial_site,
                trap_site=trap_site,
                node_coordinates=instance.coordinates,
                sink_hit_threshold=0.1,
                transfer_threshold=0.5,
            )
            msd = np.asarray(result.mean_squared_displacement_t if result.mean_squared_displacement_t is not None else np.zeros_like(times), dtype=float)
            positive = (times > times[1]) & (msd > 1e-10)
            exponent = 0.0
            if np.count_nonzero(positive) >= 3:
                exponent = float(np.polyfit(np.log(times[positive]), np.log(msd[positive]), deg=1)[0])
            graph = graph_from_adjacency(instance.adjacency)
            rows.append(
                {
                    "family": family,
                    "n_sites": int(n_sites),
                    "n_edges": graph.number_of_edges(),
                    "arrival": float(result.transport_efficiency),
                    "final_msd": float(msd[-1]) if msd.size else 0.0,
                    "final_front_width": 0.0 if result.front_width_t is None else float(result.front_width_t[-1]),
                    "participation_ratio": float(result.final_participation_ratio),
                    "ipr": float(result.final_ipr),
                    "msd_exponent": exponent,
                    "max_trace_deviation": float(result.max_trace_deviation),
                    "max_population_closure_error": float(result.max_population_closure_error),
                    "min_state_eigenvalue": float(result.min_state_eigenvalue),
                }
            )
            series[f"{family}_N{n_sites}"] = {
                "family": family,
                "n_sites": int(n_sites),
                "coordinates": instance.coordinates.tolist(),
                "adjacency": instance.adjacency.tolist(),
                "times": times.tolist(),
                "msd": msd.tolist(),
                "front_width": [] if result.front_width_t is None else result.front_width_t.tolist(),
            }
            validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(result.max_trace_deviation))
            validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(result.max_population_closure_error))
            validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(result.min_state_eigenvalue))
    return rows, validation, series


def _plot_target_map(summary_rows: list[dict[str, object]], path: Path) -> None:
    families = sorted({str(row["family"]) for row in summary_rows})
    targets = sorted({str(row["target_style"]) for row in summary_rows})
    matrix = np.full((len(families), len(targets)), np.nan)
    for i, family in enumerate(families):
        for j, target in enumerate(targets):
            values = [float(row["arrival_mean"]) for row in summary_rows if row["family"] == family and row["target_style"] == target]
            matrix[i, j] = float(np.mean(values)) if values else np.nan
    fig, ax = plt.subplots(figsize=(8.6, 5.2), constrained_layout=True)
    im = ax.imshow(matrix, cmap="magma", aspect="auto", vmin=0.0, vmax=max(1e-9, float(np.nanmax(matrix))))
    ax.set_title("Target-position effect: same network, different arrival channel")
    ax.set_xlabel("target choice")
    ax.set_ylabel("network family")
    ax.set_xticks(np.arange(len(targets)))
    ax.set_xticklabels(targets, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    fig.colorbar(im, ax=ax, label="mean target arrival")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_quantum_classical(rows: list[dict[str, object]], path: Path) -> None:
    labels = sorted({str(row["comparison_label"]) for row in rows})
    colors = {"quantum_advantage_like": "#2e7d32", "classical_explains": "#1565c0", "both_poor": "#757575", "inconclusive": "#c62828"}
    fig, ax = plt.subplots(figsize=(6.4, 6.0), constrained_layout=True)
    for label in labels:
        items = [row for row in rows if row["comparison_label"] == label]
        ax.scatter(
            [float(row["arrival_classical"]) for row in items],
            [float(row["arrival_quantum"]) for row in items],
            s=24,
            alpha=0.75,
            label=label,
            color=colors.get(label, "#424242"),
        )
    ax.plot([0, 1], [0, 1], color="black", lw=1, ls="--")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("classical target arrival")
    ax.set_ylabel("open-quantum target arrival")
    ax.set_title("Quantum/open model versus classical rate-walk control")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_quantum_classical_map(rows: list[dict[str, object]], path: Path) -> None:
    families = sorted({str(row["family"]) for row in rows})
    targets = sorted({str(row["target_style"]) for row in rows})
    matrix = np.full((len(families), len(targets)), np.nan)
    for i, family in enumerate(families):
        for j, target in enumerate(targets):
            values = [float(row["arrival_delta_quantum_minus_classical"]) for row in rows if row["family"] == family and row["target_style"] == target]
            matrix[i, j] = float(np.mean(values)) if values else np.nan
    fig, ax = plt.subplots(figsize=(8.6, 5.2), constrained_layout=True)
    limit = max(float(np.nanmax(np.abs(matrix))), 1e-9)
    im = ax.imshow(matrix, cmap="coolwarm", aspect="auto", vmin=-limit, vmax=limit)
    ax.set_title("Mean quantum-minus-classical arrival by target")
    ax.set_xlabel("target choice")
    ax.set_ylabel("network family")
    ax.set_xticks(np.arange(len(targets)))
    ax.set_xticklabels(targets, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    fig.colorbar(im, ax=ax, label="arrival difference")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_classification_panel(snapshot: dict[str, object], path: Path) -> None:
    labels = ["dynamic", "topology", "classical", "combined", "baseline"]
    values = [
        float(snapshot.get("dynamic_accuracy", 0.0)),
        float(snapshot.get("topology_accuracy", 0.0)),
        float(snapshot.get("classical_accuracy", 0.0)),
        float(snapshot.get("combined_accuracy", 0.0)),
        float(snapshot.get("combined_baseline", 0.0)),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.bar(labels, values, color=["#00897b", "#5e35b1", "#757575", "#ef6c00", "#bdbdbd"])
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("honest group-split accuracy")
    ax.set_title("Existing network-classification result reused as article evidence")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_fractals(rows: list[dict[str, object]], series: dict[str, dict[str, object]], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    example_key = next((key for key in series if key.startswith("sierpinski_gasket")), next(iter(series)))
    example = series[example_key]
    coordinates = np.asarray(example["coordinates"], dtype=float)
    adjacency = np.asarray(example["adjacency"], dtype=float)
    graph = nx.from_numpy_array(adjacency)
    positions = {index: tuple(coordinates[index]) for index in range(coordinates.shape[0])}
    nx.draw_networkx_edges(graph, positions, ax=axes[0], edge_color="#607d8b", width=1.2)
    nx.draw_networkx_nodes(graph, positions, ax=axes[0], node_color="#ffb300", node_size=70, edgecolors="black", linewidths=0.4)
    axes[0].set_title(f"Example fractal network: {example_key}")
    axes[0].axis("equal")
    axes[0].axis("off")
    for key, payload in series.items():
        if payload["n_sites"] != max(row["n_sites"] for row in rows):
            continue
        axes[1].plot(payload["times"], payload["msd"], marker="o", markersize=2, label=payload["family"])
    axes[1].set_title("Mean squared displacement")
    axes[1].set_xlabel("time")
    axes[1].set_ylabel("MSD from initial site")
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_dashboard(metrics: dict[str, object], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.0, 5.4), constrained_layout=True)
    ax.axis("off")
    text = "\n".join(
        [
            "Research Journey V2",
            "",
            f"Target effect max spread: {float(metrics.get('max_target_spread', 0.0)):.3f}",
            f"Target effect strong: {metrics.get('strong_target_effect', False)}",
            f"Mean quantum-classical delta: {float(metrics.get('mean_quantum_classical_delta', 0.0)):.3f}",
            f"Quantum-like cases: {metrics.get('quantum_advantage_like_count', 0)}",
            f"Classification combined accuracy: {float(metrics.get('classification_combined_accuracy', 0.0)):.3f}",
            f"Fractal rows: {metrics.get('fractal_record_count', 0)}",
            f"Numerics pass: {metrics.get('numerics_pass', False)}",
        ]
    )
    ax.text(0.05, 0.95, text, va="top", ha="left", fontsize=14, family="monospace")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _write_explanations(path: Path) -> None:
    payload = {
        "target_position_effect_map.png": {
            "title": "Efeito da posição do alvo",
            "axes": "Eixo horizontal: tipo de alvo. Eixo vertical: família da rede. Cor: chegada média ao canal de sucesso.",
            "reading": "Se a cor muda muito na mesma linha, trocar só o alvo muda a física do transporte.",
        },
        "quantum_vs_classical_delta_map.png": {
            "title": "Diferença quântico menos clássico",
            "axes": "Cor vermelha favorece o modelo quântico aberto; azul favorece ou aproxima o controle clássico.",
            "reading": "Serve para separar assinatura quântica de efeito trivial de conectividade.",
        },
        "classification_article_panel.png": {
            "title": "Classificação de redes",
            "axes": "Barras mostram acurácia com split honesto por instância de grafo.",
            "reading": "Dinâmica ajuda, mas o melhor resultado vem de dinâmica mais topologia.",
        },
        "fractal_msd_and_geometry.png": {
            "title": "Fractais e espalhamento",
            "axes": "Painel esquerdo: geometria. Painel direito: MSD ao longo do tempo.",
            "reading": "MSD menor ou curva com formato diferente indica que a geometria altera a propagação.",
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_summary(output_dir: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Research Journey V2",
        "",
        "## Pergunta Central",
        "",
        "Onde colocamos o canal de chegada muda a física, e a dinâmica quântica aberta carrega informação sobre a rede além de uma caminhada clássica simples?",
        "",
        "## Resultados Principais",
        "",
        f"- Maior spread por trocar alvo: `{float(metrics.get('max_target_spread', 0.0)):.3f}`.",
        f"- Efeito forte de alvo pelo critério CI95 > 0.05: `{metrics.get('strong_target_effect', False)}`.",
        f"- Diferença média quântico - clássico: `{float(metrics.get('mean_quantum_classical_delta', 0.0)):.3f}`.",
        f"- Casos quantum_advantage_like: `{metrics.get('quantum_advantage_like_count', 0)}`.",
        f"- Classificação combinada reaproveitada: `{float(metrics.get('classification_combined_accuracy', 0.0)):.3f}`.",
        f"- Validação numérica passou: `{metrics.get('numerics_pass', False)}`.",
        "",
        "## Como Ler",
        "",
        "`arrival` é a população que chegou ao canal de sucesso. `target` ou alvo é o nó que drena para esse canal. `gamma/J` mede o quanto o ambiente embaralha fase comparado com o acoplamento coerente. `W/J` mede a irregularidade local comparada com o acoplamento coerente.",
        "",
        "## Material-Inspired",
        "",
        "Fotossíntese, perovskitas e simuladores de qubits entram como motivação. O modelo aqui continua efetivo: redes finitas, excitação única, ruído de fase, perda e canal de chegada.",
        "",
        "## Próximo Passo",
        "",
        "Escolher o par de redes ou alvos com maior contraste e rodar uma confirmação local com mais seeds.",
        "",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_notebook(notebook_path: Path) -> None:
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Transport Research Journey V2\n",
                    "\n",
                    "Notebook guiado para olhar a jornada pós-classificação: alvo/geometria, quântico vs clássico, classificação, fractais e motivação material.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from pathlib import Path\n",
                    "import json\n",
                    "import pandas as pd\n",
                    "from IPython.display import Image, Markdown, display\n",
                    "\n",
                    "ROOT = Path.cwd()\n",
                    "if not (ROOT / 'pyproject.toml').exists():\n",
                    "    ROOT = ROOT.parent\n",
                    "OUT = ROOT / 'outputs' / 'transport_networks' / 'research_journey_v2' / 'latest'\n",
                    "OUT\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## Rodar A Jornada\n",
                    "\n",
                    "Edite o perfil se quiser. `smoke` testa rápido, `interactive` é o padrão para estudar, `paper` é mais pesado.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# !python scripts/run_transport_research_journey_v2.py --profile smoke\n",
                    "# !python scripts/run_transport_research_journey_v2.py --profile interactive\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Resumo\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "metrics = json.loads((OUT / 'metrics.json').read_text(encoding='utf-8'))\n",
                    "display(Markdown((OUT / 'summary.md').read_text(encoding='utf-8')))\n",
                    "metrics\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Figuras Principais E Como Ler\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "explanations = json.loads((OUT / 'figure_explanations_ptbr.json').read_text(encoding='utf-8'))\n",
                    "for name in ['target_position_effect_map.png', 'quantum_vs_classical_delta_map.png', 'classification_article_panel.png', 'fractal_msd_and_geometry.png', 'research_journey_dashboard.png']:\n",
                    "    path = OUT / 'figures' / name\n",
                    "    if path.exists():\n",
                    "        info = explanations.get(name, {})\n",
                    "        display(Markdown(f\"### {info.get('title', name)}\\n\\n{info.get('axes', '')}\\n\\n{info.get('reading', '')}\"))\n",
                    "        display(Image(filename=str(path)))\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Tabelas Para Investigar\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "for filename in ['target_geometry_summary.csv', 'quantum_classical_comparison.csv', 'fractal_transport_summary.csv']:\n",
                    "    path = OUT / filename\n",
                    "    if path.exists():\n",
                    "        display(Markdown(f'### {filename}'))\n",
                    "        display(pd.read_csv(path).head(20))\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Motivação Material Sem Exagero\n"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "display(Markdown((OUT / 'material_motivation_table.md').read_text(encoding='utf-8')))\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    notebook_path.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_latest(output_dir: Path, latest_dir: Path) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        target = latest_dir / path.name
        if path.is_dir():
            target.mkdir(exist_ok=True)
            for child in path.iterdir():
                if child.is_file():
                    (target / child.name).write_bytes(child.read_bytes())
        elif path.is_file():
            target.write_bytes(path.read_bytes())


def run_journey(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    target_rows, target_validation = _target_rows(config)
    target_summary = _target_summary(target_rows)
    target_effect = _target_effect(target_rows)
    qc_rows, classical_validation = _quantum_classical_rows(target_rows, config)
    fractal_rows, fractal_validation, fractal_series = _fractal_rows(config)
    classification = _classification_snapshot()

    qc_deltas = [float(row["arrival_delta_quantum_minus_classical"]) for row in qc_rows]
    comparison_counts = defaultdict(int)
    for row in qc_rows:
        comparison_counts[str(row["comparison_label"])] += 1
    validation = {
        "max_trace_deviation": max(float(target_validation["max_trace_deviation"]), float(fractal_validation["max_trace_deviation"])),
        "max_population_closure_error": max(float(target_validation["max_population_closure_error"]), float(fractal_validation["max_population_closure_error"])),
        "min_state_eigenvalue": min(float(target_validation["min_state_eigenvalue"]), float(fractal_validation["min_state_eigenvalue"])),
        "classical_max_population_closure_error": float(classical_validation["classical_max_population_closure_error"]),
    }
    numerics_pass = bool(
        validation["max_trace_deviation"] < 1e-8
        and validation["max_population_closure_error"] < 1e-8
        and validation["min_state_eigenvalue"] > -1e-7
        and validation["classical_max_population_closure_error"] < 1e-8
    )
    metrics = {
        "profile": config["profile"],
        "target_record_count": len(target_rows),
        "quantum_classical_record_count": len(qc_rows),
        "fractal_record_count": len(fractal_rows),
        "validation": validation,
        "numerics_pass": numerics_pass,
        **target_effect,
        "mean_quantum_classical_delta": float(np.mean(qc_deltas)) if qc_deltas else 0.0,
        "quantum_advantage_like_count": int(comparison_counts["quantum_advantage_like"]),
        "classical_explains_count": int(comparison_counts["classical_explains"]),
        "both_poor_count": int(comparison_counts["both_poor"]),
        "inconclusive_count": int(comparison_counts["inconclusive"]),
        "classification_available": bool(classification.get("available", False)),
        "classification_dynamic_accuracy": float(classification.get("dynamic_accuracy", 0.0)),
        "classification_topology_accuracy": float(classification.get("topology_accuracy", 0.0)),
        "classification_classical_accuracy": float(classification.get("classical_accuracy", 0.0)),
        "classification_combined_accuracy": float(classification.get("combined_accuracy", 0.0)),
        "classification_combined_baseline": float(classification.get("combined_baseline", 0.0)),
    }

    _write_csv(target_rows, output_dir / "target_geometry_records.csv")
    _write_csv(target_summary, output_dir / "target_geometry_summary.csv")
    _write_csv(qc_rows, output_dir / "quantum_classical_comparison.csv")
    _write_csv(fractal_rows, output_dir / "fractal_transport_summary.csv")
    (output_dir / "fractal_series.json").write_text(json.dumps(fractal_series, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown_table(MATERIAL_ROWS, output_dir / "material_motivation_table.md")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat()}, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_summary(output_dir, metrics)
    _write_explanations(output_dir / "figure_explanations_ptbr.json")

    _plot_target_map(target_summary, figures_dir / "target_position_effect_map.png")
    _plot_quantum_classical(qc_rows, figures_dir / "quantum_vs_classical_scatter.png")
    _plot_quantum_classical_map(qc_rows, figures_dir / "quantum_vs_classical_delta_map.png")
    _plot_classification_panel(classification, figures_dir / "classification_article_panel.png")
    _plot_fractals(fractal_rows, fractal_series, figures_dir / "fractal_msd_and_geometry.png")
    _plot_dashboard(metrics, figures_dir / "research_journey_dashboard.png")
    _write_notebook(ROOT / "notebooks" / "transport_research_journey_v2.ipynb")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the integrated post-classification research journey for open quantum transport.")
    parser.add_argument("--profile", choices=["smoke", "interactive", "paper"], default="smoke")
    parser.add_argument("--output-subdir", default="research_journey_v2")
    args = parser.parse_args(argv)
    config = profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_journey(config, output_dir)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
