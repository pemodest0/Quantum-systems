from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import (  # noqa: E402
    DYNAMIC_SIGNATURE_FEATURES,
    SUPPORTED_DYNAMIC_NETWORK_FAMILIES,
    NetworkInstance,
    classification_result_to_dict,
    classify_records,
    generate_network_instance,
    signature_from_dephasing_scan,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
    write_literature_guardrails,
    write_signature_csv,
)


LITERATURE_GUARDRAILS = [
    {
        "key": "MulkenBlumen2011",
        "url": "https://doi.org/10.1016/j.physrep.2011.01.002",
        "benchmark": "closed_ctqw_topology",
        "reading": "Continuous-time quantum-walk transport depends strongly on graph topology; return probability and spreading are standard closed-system diagnostics.",
    },
    {
        "key": "MulkenPerniceBlumen2007",
        "url": "https://doi.org/10.1103/PhysRevE.76.051125",
        "benchmark": "closed_ctqw_topology",
        "reading": "Small-world shortcuts can speed coherent spreading while still preserving non-classical memory of the initial node.",
    },
    {
        "key": "RazzoliParisBordone2021",
        "url": "https://doi.org/10.3390/e23010085",
        "benchmark": "trap_target_placement",
        "reading": "Trap position, graph structure, and initial state determine transport efficiency; connectivity alone is not a reliable global predictor.",
    },
    {
        "key": "Mohseni2008",
        "url": "https://doi.org/10.1063/1.3002335",
        "benchmark": "dephasing_assisted_transport",
        "reading": "Moderate environmental dephasing can enhance transport when purely coherent motion is hindered by interference or disorder.",
    },
    {
        "key": "PlenioHuelga2008",
        "url": "https://doi.org/10.1088/1367-2630/10/11/113019",
        "benchmark": "dephasing_assisted_transport",
        "reading": "Local dephasing can assist excitation transport, but excessive dephasing suppresses useful motion.",
    },
    {
        "key": "Rebentrost2009",
        "url": "https://doi.org/10.1088/1367-2630/11/3/033003",
        "benchmark": "dephasing_assisted_transport",
        "reading": "Efficiency maps over static disorder and dephasing are a standard way to diagnose environment-assisted transport.",
    },
    {
        "key": "RossiTorselloHancock2015",
        "url": "https://doi.org/10.1103/PhysRevE.91.022815",
        "benchmark": "dynamic_graph_similarity",
        "reading": "Graph similarity can be probed by continuous-time quantum-walk evolution and quantum-state divergence.",
    },
    {
        "key": "MinelloRossiTorsello2019",
        "url": "https://doi.org/10.3390/e21030328",
        "benchmark": "dynamic_graph_similarity",
        "reading": "Quantum-walk-based graph similarity can be used in graph classification tasks.",
    },
    {
        "key": "Gamble2010",
        "url": "https://doi.org/10.1103/PhysRevA.81.052313",
        "benchmark": "limits_guardrail",
        "reading": "Quantum-walk signatures are not universal graph-isomorphism solvers; highly symmetric graphs can remain difficult.",
    },
    {
        "key": "Maier2019",
        "url": "https://doi.org/10.1103/PhysRevLett.122.050501",
        "benchmark": "dephasing_assisted_transport",
        "reading": "Controlled quantum simulators observe a crossover from coherent/localized dynamics to assisted transport and high-noise suppression.",
    },
]


def _profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": profile,
            "families": ["chain", "ring", "star", "complete"],
            "edge_models_main": ["unweighted"],
            "edge_models_sensitivity": ["unweighted", "degree_normalized"],
            "n_sites_values": [6],
            "graph_realizations": 1,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 4100,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "dephasing_over_coupling": [0.0, 0.2, 0.6],
            "target_styles": ["near", "far"],
            "t_final_closed": 8.0,
            "t_final_open": 9.0,
            "n_time_samples": 80,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    if profile == "interactive":
        return {
            "profile": profile,
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "edge_models_main": ["unweighted"],
            "edge_models_sensitivity": ["unweighted", "degree_normalized", "exponential_distance", "power_law_distance"],
            "edge_sensitivity_families": ["chain", "ring", "modular_two_community", "random_geometric"],
            "n_sites_values": [8],
            "graph_realizations": 3,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7],
            "graph_seed_base": 4200,
            "disorder_strength_over_coupling": [0.0, 0.6, 1.0],
            "dephasing_over_coupling": [0.0, 0.05, 0.2, 0.6],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final_closed": 10.0,
            "t_final_open": 12.0,
            "n_time_samples": 120,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    if profile == "confirm":
        return {
            "profile": profile,
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "edge_models_main": ["unweighted", "exponential_distance"],
            "edge_models_sensitivity": ["unweighted", "degree_normalized", "exponential_distance", "power_law_distance"],
            "edge_sensitivity_families": ["chain", "ring", "modular_two_community", "random_geometric"],
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 8,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23],
            "graph_seed_base": 4300,
            "disorder_strength_over_coupling": [0.0, 0.3, 0.6, 0.9, 1.2],
            "dephasing_over_coupling": [0.0, 0.03, 0.05, 0.1, 0.2, 0.4, 0.8],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final_closed": 12.0,
            "t_final_open": 16.0,
            "n_time_samples": 180,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _is_deterministic_family(family: str) -> bool:
    return family in {"chain", "ring", "complete", "star", "square_lattice_2d", "bottleneck", "clustered"}


def _edge_length_scale(adjacency: np.ndarray, coordinates: np.ndarray) -> float:
    rows, cols = np.nonzero(np.triu(adjacency, k=1))
    if rows.size == 0:
        return 1.0
    distances = np.linalg.norm(coordinates[rows] - coordinates[cols], axis=1)
    distances = distances[distances > 1e-12]
    if distances.size == 0:
        return 1.0
    return float(np.median(distances))


def _weighted_adjacency(instance: NetworkInstance, edge_model: str) -> np.ndarray:
    adjacency = np.asarray(instance.adjacency, dtype=float)
    coordinates = np.asarray(instance.coordinates, dtype=float)
    if edge_model == "unweighted":
        return adjacency.copy()
    if edge_model == "degree_normalized":
        degrees = np.sum(adjacency > 0.0, axis=1).astype(float)
        scale = np.sqrt(np.outer(np.maximum(degrees, 1.0), np.maximum(degrees, 1.0)))
        weighted = np.divide(adjacency, scale, out=np.zeros_like(adjacency), where=scale > 0.0)
    elif edge_model in {"exponential_distance", "power_law_distance"}:
        scale = _edge_length_scale(adjacency, coordinates)
        distances = np.linalg.norm(coordinates[:, None, :] - coordinates[None, :, :], axis=2)
        distances = np.maximum(distances, 1e-12)
        if edge_model == "exponential_distance":
            weighted = adjacency * np.exp(-distances / max(scale, 1e-12))
        else:
            weighted = adjacency / np.maximum(distances / max(scale, 1e-12), 1e-12) ** 3
    else:
        raise ValueError(f"unsupported edge model: {edge_model}")
    max_weight = float(np.max(weighted))
    if max_weight > 1e-12:
        weighted = weighted / max_weight
    weighted = 0.5 * (weighted + weighted.T)
    np.fill_diagonal(weighted, 0.0)
    return weighted


def _weighted_instance(instance: NetworkInstance, edge_model: str) -> NetworkInstance:
    return NetworkInstance(
        family=instance.family,
        instance_id=f"{instance.instance_id}_edge-{edge_model}",
        adjacency=_weighted_adjacency(instance, edge_model),
        coordinates=instance.coordinates,
        labels=instance.labels,
        seed=instance.seed,
        metadata={**instance.metadata, "edge_model": edge_model},
    )


def _mean_or_nan(values: list[float]) -> float:
    if not values:
        return float("nan")
    return float(np.mean(values))


def _closed_walk_benchmark(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], dict[str, float]]:
    records: list[dict[str, object]] = []
    series: dict[str, dict[str, object]] = {}
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final_closed"]), int(config["n_time_samples"]))
    for family in list(config["families"]):
        n_sites = int(list(config["n_sites_values"])[0])
        instance = generate_network_instance(str(family), n_sites=n_sites, seed=int(config["graph_seed_base"]) + n_sites)
        weighted = _weighted_instance(instance, "unweighted")
        return_curves = []
        participation_curves = []
        for initial_site in range(n_sites):
            result = simulate_transport(
                adjacency=weighted.adjacency,
                coupling_hz=float(config["coupling_hz"]),
                dephasing_rate_hz=0.0,
                sink_rate_hz=0.0,
                loss_rate_hz=0.0,
                times=times,
                initial_site=initial_site,
                trap_site=0 if initial_site != 0 else 1,
                node_coordinates=weighted.coordinates,
            )
            return_curves.append(result.node_populations[:, initial_site])
            participation_curves.append(result.participation_ratio_t)
            validation["max_trace_deviation"] = max(validation["max_trace_deviation"], result.max_trace_deviation)
            validation["max_population_closure_error"] = max(validation["max_population_closure_error"], result.max_population_closure_error)
            validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], result.min_state_eigenvalue)
        average_return = np.mean(np.asarray(return_curves), axis=0)
        average_participation = np.mean(np.asarray(participation_curves), axis=0)
        leave_candidates = np.flatnonzero(average_return <= 0.5)
        records.append(
            {
                "benchmark": "closed_ctqw_topology",
                "family": family,
                "n_sites": n_sites,
                "edge_model": "unweighted",
                "long_time_average_return": float(np.mean(average_return[len(average_return) // 2 :])),
                "minimum_average_return": float(np.min(average_return)),
                "maximum_average_participation": float(np.max(average_participation)),
                "time_to_average_return_below_half": None if leave_candidates.size == 0 else float(times[int(leave_candidates[0])]),
                "literature_expectation": "Topology changes coherent spreading and return probability; no sink or dephasing should conserve network population.",
            }
        )
        series[str(family)] = {
            "times": times.tolist(),
            "average_return": average_return.tolist(),
            "average_participation": average_participation.tolist(),
        }
    return records, series, validation


def _build_open_scan_records(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], dict[str, object]]:
    records: list[dict[str, object]] = []
    example_series: dict[str, dict[str, object]] = {}
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    random_families = {"erdos_renyi", "watts_strogatz_small_world", "barabasi_albert_scale_free", "modular_two_community", "random_geometric"}
    times = np.linspace(0.0, float(config["t_final_open"]), int(config["n_time_samples"]))
    dephasing_grid = np.asarray(config["dephasing_over_coupling"], dtype=float)
    disorder_grid = np.asarray(config["disorder_strength_over_coupling"], dtype=float)
    edge_sensitivity_families = set(config.get("edge_sensitivity_families", config["families"]))

    for family in list(config["families"]):
        realization_count = int(config["deterministic_graph_realizations"]) if _is_deterministic_family(str(family)) else int(config["graph_realizations"])
        for n_sites in list(config["n_sites_values"]):
            for realization in range(realization_count):
                graph_seed = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * realization + len(records)
                if family not in random_families:
                    graph_seed = int(config["graph_seed_base"]) + int(n_sites) + realization
                base = generate_network_instance(str(family), n_sites=int(n_sites), seed=graph_seed, realization_index=realization)
                initial_site = int(n_sites) - 1
                candidates = target_candidates(base, initial_site=initial_site)
                edge_models = list(config["edge_models_main"])
                if str(family) in edge_sensitivity_families:
                    edge_models = sorted(set(edge_models).union(set(config["edge_models_sensitivity"])))
                for edge_model in edge_models:
                    instance = _weighted_instance(base, str(edge_model))
                    for target_style in list(config["target_styles"]):
                        if target_style not in candidates:
                            continue
                        trap_site = int(candidates[target_style])
                        topo = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
                        rows, cols = np.nonzero(np.triu(instance.adjacency, k=1))
                        edge_weights = instance.adjacency[rows, cols] if rows.size else np.asarray([0.0])
                        topo["edge_weight_mean"] = float(np.mean(edge_weights))
                        topo["edge_weight_std"] = float(np.std(edge_weights))
                        topo["edge_weight_min"] = float(np.min(edge_weights))
                        topo["edge_weight_max"] = float(np.max(edge_weights))
                        for disorder_strength in disorder_grid:
                            for disorder_seed in list(config["disorder_seeds"]):
                                seed = int(disorder_seed) + 17 * graph_seed + int(round(1000 * float(disorder_strength)))
                                site_energies = static_disorder_energies(int(n_sites), float(disorder_strength) * float(config["coupling_hz"]), seed=seed)
                                scan_results = [
                                    simulate_transport(
                                        adjacency=instance.adjacency,
                                        coupling_hz=float(config["coupling_hz"]),
                                        dephasing_rate_hz=float(gamma) * float(config["coupling_hz"]),
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
                                    for gamma in dephasing_grid
                                ]
                                record = signature_from_dephasing_scan(
                                    scan_results=scan_results,
                                    dephasing_over_coupling=dephasing_grid,
                                    coupling_hz=float(config["coupling_hz"]),
                                    family=str(family),
                                    instance_id=instance.instance_id,
                                    graph_seed=graph_seed,
                                    disorder_seed=int(disorder_seed),
                                    disorder_strength_over_coupling=float(disorder_strength),
                                    target_style=str(target_style),
                                    initial_site=initial_site,
                                    trap_site=trap_site,
                                    topology=topo,
                                )
                                record["edge_model"] = str(edge_model)
                                record["record_id"] = f"{record['record_id']}_edge-{edge_model}"
                                records.append(record)
                                best_index = int(np.argmax([result.transport_efficiency for result in scan_results]))
                                best = scan_results[best_index]
                                example_series[str(record["record_id"])] = {
                                    "family": str(family),
                                    "edge_model": str(edge_model),
                                    "target_style": str(target_style),
                                    "times": best.times.tolist(),
                                    "node_populations": best.node_populations.tolist(),
                                    "sink_population": best.sink_population.tolist(),
                                    "loss_population": best.loss_population.tolist(),
                                }
                                validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(record["max_trace_deviation"]))
                                validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(record["max_population_closure_error"]))
                                validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(record["min_state_eigenvalue"]))
    return records, example_series, validation


def _target_position_benchmark(open_records: list[dict[str, object]]) -> list[dict[str, object]]:
    min_seed = min(int(item["disorder_seed"]) for item in open_records)
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for record in open_records:
        if str(record["edge_model"]) != "unweighted":
            continue
        if abs(float(record["disorder_strength_over_coupling"])) > 1e-12:
            continue
        if int(record["disorder_seed"]) != min_seed:
            continue
        grouped[(str(record["family"]), str(record["instance_id"]), str(record["target_style"]))].append(record)
    rows: list[dict[str, object]] = []
    for (family, instance_id, target_style), items in grouped.items():
        values = [float(item["zero_dephasing_arrival"]) for item in items]
        rows.append(
            {
                "benchmark": "trap_target_placement",
                "family": family,
                "instance_id": instance_id,
                "target_style": target_style,
                "edge_model": "unweighted",
                "mean_zero_dephasing_arrival": _mean_or_nan(values),
                "mean_target_degree": _mean_or_nan([float(item["topology_target_degree"]) for item in items]),
                "mean_initial_target_distance": _mean_or_nan([float(item["topology_initial_target_distance"]) for item in items]),
                "literature_expectation": "Changing only trap/target placement can change transport; degree alone should not be treated as a sufficient predictor.",
            }
        )
    return rows


def _classification_reports(records: list[dict[str, object]]) -> dict[str, object]:
    unweighted = [record for record in records if str(record["edge_model"]) == "unweighted"]
    dynamic_features = [name for name in DYNAMIC_SIGNATURE_FEATURES if name in unweighted[0]]
    topology_features = sorted([name for name in unweighted[0] if name.startswith("topology_")])
    combined_features = dynamic_features + topology_features
    reports: dict[str, object] = {
        "dynamic_only_family": classification_result_to_dict(classify_records(unweighted, feature_names=dynamic_features, label_name="family")),
        "topology_only_family": classification_result_to_dict(classify_records(unweighted, feature_names=topology_features, label_name="family")),
        "combined_family": classification_result_to_dict(classify_records(unweighted, feature_names=combined_features, label_name="family")),
    }
    edge_labels = sorted({str(record["edge_model"]) for record in records})
    if len(edge_labels) > 1:
        reports["dynamic_only_edge_model"] = classification_result_to_dict(classify_records(records, feature_names=dynamic_features, label_name="edge_model"))
    return reports


def _benchmark_metrics(
    *,
    config: dict[str, object],
    closed_records: list[dict[str, object]],
    open_records: list[dict[str, object]],
    target_records: list[dict[str, object]],
    classification_reports: dict[str, object],
    validation: dict[str, object],
) -> dict[str, object]:
    gain_candidates = [
        record
        for record in open_records
        if float(record["dephasing_gain"]) >= 0.05 and float(record["best_dephasing_over_coupling"]) > 0.0
    ]
    strongest_gain = max(open_records, key=lambda record: float(record["dephasing_gain"]))
    by_instance = defaultdict(list)
    for row in target_records:
        by_instance[(row["family"], row["instance_id"])].append(float(row["mean_zero_dephasing_arrival"]))
    target_spreads = [max(values) - min(values) for values in by_instance.values() if len(values) > 1]
    dynamic_report = classification_reports["dynamic_only_family"]
    topology_report = classification_reports["topology_only_family"]
    combined_report = classification_reports["combined_family"]
    return {
        "profile": config["profile"],
        "closed_record_count": len(closed_records),
        "open_signature_count": len(open_records),
        "target_position_record_count": len(target_records),
        "families": sorted({str(record["family"]) for record in open_records}),
        "edge_models": sorted({str(record["edge_model"]) for record in open_records}),
        "largest_dephasing_gain": float(strongest_gain["dephasing_gain"]),
        "largest_dephasing_gain_family": strongest_gain["family"],
        "largest_dephasing_gain_target_style": strongest_gain["target_style"],
        "largest_dephasing_gain_edge_model": strongest_gain["edge_model"],
        "useful_dephasing_candidate_count": len(gain_candidates),
        "max_target_position_spread": float(max(target_spreads) if target_spreads else 0.0),
        "dynamic_only_family_accuracy": dynamic_report["accuracy"],
        "topology_only_family_accuracy": topology_report["accuracy"],
        "combined_family_accuracy": combined_report["accuracy"],
        "family_baseline_accuracy": combined_report["baseline_accuracy"],
        "validation": validation,
        "acceptance": {
            "numerics_pass": bool(
                float(validation["max_trace_deviation"]) < 1e-8
                and float(validation["max_population_closure_error"]) < 1e-8
                and float(validation["min_state_eigenvalue"]) > -1e-7
            ),
            "target_position_matters_candidate": bool((max(target_spreads) if target_spreads else 0.0) >= 0.05),
            "dephasing_assistance_candidate": bool(len(gain_candidates) > 0),
            "dynamic_classification_above_baseline": bool(float(dynamic_report["accuracy"]) > float(dynamic_report["baseline_accuracy"])),
            "combined_classification_above_baseline": bool(float(combined_report["accuracy"]) > float(combined_report["baseline_accuracy"])),
            "dynamics_adds_beyond_topology_candidate": bool(float(combined_report["accuracy"]) > float(topology_report["accuracy"]) + 1e-12),
        },
    }


def _plot_closed_return(series: dict[str, dict[str, object]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5), constrained_layout=True)
    for family, payload in sorted(series.items()):
        ax.plot(payload["times"], payload["average_return"], lw=2.0, label=family)
    ax.set_title("Closed quantum walk benchmark: average return probability")
    ax.set_xlabel("time in units of 1/J")
    ax.set_ylabel("average probability of still being at the starting node")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_target_position(target_records: list[dict[str, object]], output_path: Path) -> None:
    families = sorted({str(row["family"]) for row in target_records})
    targets = sorted({str(row["target_style"]) for row in target_records})
    if not families or not targets:
        fig, ax = plt.subplots(figsize=(7.0, 3.0), constrained_layout=True)
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "Target-position benchmark not applicable\nfor this focused campaign.",
            ha="center",
            va="center",
            fontsize=11,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=220)
        plt.close(fig)
        return
    matrix = np.full((len(families), len(targets)), np.nan)
    for i, family in enumerate(families):
        for j, target in enumerate(targets):
            values = [float(row["mean_zero_dephasing_arrival"]) for row in target_records if row["family"] == family and row["target_style"] == target]
            matrix[i, j] = _mean_or_nan(values)
    fig, ax = plt.subplots(figsize=(8.5, max(4.5, 0.35 * len(families) + 2.5)), constrained_layout=True)
    finite_values = matrix[np.isfinite(matrix)]
    vmax = max(1e-9, float(np.max(finite_values))) if finite_values.size else 1e-9
    im = ax.imshow(matrix, aspect="auto", cmap="magma", vmin=0.0, vmax=vmax)
    ax.set_title("Trap/target placement benchmark at zero dephasing")
    ax.set_xlabel("target choice")
    ax.set_ylabel("network family")
    ax.set_xticks(np.arange(len(targets)))
    ax.set_xticklabels(targets, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    fig.colorbar(im, ax=ax, label="arrival at target")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_dephasing_gain(records: list[dict[str, object]], output_path: Path) -> None:
    unweighted = [record for record in records if str(record["edge_model"]) == "unweighted"]
    families = sorted({str(record["family"]) for record in unweighted})
    disorder = sorted({float(record["disorder_strength_over_coupling"]) for record in unweighted})
    matrix = np.full((len(families), len(disorder)), np.nan)
    for i, family in enumerate(families):
        for j, strength in enumerate(disorder):
            values = [
                float(record["dephasing_gain"])
                for record in unweighted
                if str(record["family"]) == family and abs(float(record["disorder_strength_over_coupling"]) - strength) < 1e-12
            ]
            matrix[i, j] = _mean_or_nan(values)
    fig, ax = plt.subplots(figsize=(8.5, max(4.5, 0.35 * len(families) + 2.5)), constrained_layout=True)
    limit = max(abs(float(np.nanmin(matrix))), abs(float(np.nanmax(matrix))), 1e-9)
    im = ax.imshow(matrix, aspect="auto", cmap="coolwarm", vmin=-limit, vmax=limit)
    ax.set_title("Dephasing-assistance benchmark")
    ax.set_xlabel("static disorder strength / coherent coupling")
    ax.set_ylabel("network family")
    ax.set_xticks(np.arange(len(disorder)))
    ax.set_xticklabels([f"{value:.2f}" for value in disorder])
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    fig.colorbar(im, ax=ax, label="best arrival minus zero-dephasing arrival")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_classification_controls(reports: dict[str, object], output_path: Path) -> None:
    labels = ["majority baseline", "dynamic only", "topology only", "dynamic + topology"]
    combined = reports["combined_family"]
    values = [
        float(combined["baseline_accuracy"]),
        float(reports["dynamic_only_family"]["accuracy"]),
        float(reports["topology_only_family"]["accuracy"]),
        float(combined["accuracy"]),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 5.2), constrained_layout=True)
    ax.bar(labels, values, color=["#94a3b8", "#2563eb", "#0f766e", "#7c2d12"])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("test accuracy")
    ax.set_title("Family classification controls")
    ax.tick_params(axis="x", rotation=20)
    for index, value in enumerate(values):
        ax.text(index, value + 0.025, f"{value:.2f}", ha="center", va="bottom")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_edge_sensitivity(records: list[dict[str, object]], output_path: Path) -> None:
    edge_models = sorted({str(record["edge_model"]) for record in records})
    families = sorted({str(record["family"]) for record in records})
    matrix = np.full((len(families), len(edge_models)), np.nan)
    for i, family in enumerate(families):
        for j, edge_model in enumerate(edge_models):
            values = [
                float(record["best_arrival"])
                for record in records
                if str(record["family"]) == family and str(record["edge_model"]) == edge_model
            ]
            matrix[i, j] = _mean_or_nan(values)
    fig, ax = plt.subplots(figsize=(9.0, max(4.5, 0.35 * len(families) + 2.5)), constrained_layout=True)
    im = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0.0, vmax=max(1e-9, float(np.nanmax(matrix))))
    ax.set_title("Edge-weight model sensitivity")
    ax.set_xlabel("edge model")
    ax.set_ylabel("network family")
    ax.set_xticks(np.arange(len(edge_models)))
    ax.set_xticklabels(edge_models, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    fig.colorbar(im, ax=ax, label="mean best target arrival")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_example_dynamics(example: dict[str, object], output_path: Path) -> None:
    times = np.asarray(example["times"], dtype=float)
    populations = np.asarray(example["node_populations"], dtype=float)
    sink = np.asarray(example["sink_population"], dtype=float)
    loss = np.asarray(example["loss_population"], dtype=float)
    fig, ax = plt.subplots(figsize=(9.0, 5.4), constrained_layout=True)
    for site in range(populations.shape[1]):
        ax.plot(times, populations[:, site], lw=0.9, alpha=0.45)
    ax.plot(times, sink, lw=2.7, color="#15803d", label="successful target arrival")
    ax.plot(times, loss, lw=2.0, color="#b91c1c", label="unwanted loss")
    ax.set_title(f"Population dynamics example: {example['family']} / {example['target_style']} / {example['edge_model']}")
    ax.set_xlabel("time in units of 1/J")
    ax.set_ylabel("population")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_methodology(output_dir: Path, config: dict[str, object]) -> None:
    lines = [
        "# Methodological benchmark protocol",
        "",
        "## Scientific question",
        "",
        "Can the time evolution of one excitation identify the network family and the physical transport regime?",
        "",
        "## Controls",
        "",
        "1. Closed coherent walk: sink, loss, dephasing, and disorder are set to zero. This checks topology-dependent spreading without open-system channels.",
        "2. Trap/target placement: dephasing and disorder are set to zero, and only the target position is changed.",
        "3. Dephasing-assisted transport: static disorder is fixed per seed, and dephasing is scanned against the zero-dephasing control.",
        "4. Dynamic classification: dynamic signatures are classified and compared against topology-only and majority-baseline controls.",
        "5. Edge-weight sensitivity: representative graph families are rerun with alternative edge-weight laws.",
        "",
        "## Normalizations",
        "",
        "- Time is reported in units of 1/J, where J is the coherent coupling scale.",
        "- Disorder means local site-energy irregularity divided by J.",
        "- Dephasing means phase-scrambling rate divided by J.",
        "- Target arrival means accumulated population in the successful arrival channel.",
        "- Entropy, purity, participation ratio, and IPR are computed on the graph-only normalized state unless otherwise stated by the simulator payload.",
        "",
        "## Acceptance rules",
        "",
        "- Numerical validity requires trace and population closure errors below 1e-8 and minimum eigenvalue above -1e-7.",
        "- A dephasing-assistance candidate requires gain >= 0.05 and best dephasing > 0.",
        "- A target-placement candidate requires target-position spread >= 0.05 inside the same graph instance.",
        "- A dynamic-classification candidate must beat the majority baseline.",
        "- No run is interpreted as a final physics claim unless it survives a larger ensemble confirmation.",
        "",
        "## Profile used",
        "",
        "```json",
        json.dumps(config, indent=2, ensure_ascii=False),
        "```",
    ]
    (output_dir / "methodology.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plain_ptbr_explanations(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "closed_walk_return_probability.png": {
            "title_meaning": "Mostra se a excitacao fica presa perto do ponto inicial ou se se espalha pela rede.",
            "x_axis": "Tempo medido em unidades de 1/J. J e a forca basica de passagem entre nos ligados.",
            "y_axis": "Probabilidade media de encontrar a excitacao no no onde ela comecou.",
            "expected": "A literatura espera curvas diferentes para topologias diferentes, porque cada rede interfere e espalha de um jeito.",
            "measured": "Use este painel como controle sem alvo, sem perda, sem ruido e sem desordem.",
        },
        "trap_position_sensitivity.png": {
            "title_meaning": "Mostra quanto a escolha do alvo muda a chegada da excitacao.",
            "x_axis": "Tipo de alvo escolhido: perto, longe, central ou pouco central.",
            "y_axis": "Familia de rede.",
            "color": "Cor mais clara significa maior chegada ao alvo.",
            "expected": "Razzoli et al. esperam que a posicao do trap/alvo importe e que conectividade sozinha nao explique tudo.",
            "measured": f"Maior diferenca encontrada entre posicoes de alvo: {float(metrics['max_target_position_spread']):.3f}.",
        },
        "dephasing_assistance_window.png": {
            "title_meaning": "Mostra onde bagunca de fase ajuda ou atrapalha a chegada ao alvo.",
            "x_axis": "Irregularidade fixa da rede comparada com J.",
            "y_axis": "Familia de rede.",
            "color": "Vermelho positivo significa que algum ruido melhorou a chegada; azul negativo significa que piorou.",
            "expected": "Mohseni, Plenio e Rebentrost esperam ajuda em regime intermediario, nao em ruido muito forte.",
            "measured": f"Maior ganho encontrado: {float(metrics['largest_dephasing_gain']):.3f}.",
        },
        "classification_controls.png": {
            "title_meaning": "Compara se a rede pode ser reconhecida pela dinamica, pela topologia estatica, ou pelas duas juntas.",
            "x_axis": "Tipo de informacao entregue ao classificador.",
            "y_axis": "Acerto no teste.",
            "expected": "Se a dinamica carrega uma impressao digital real, dynamic only deve superar o chute majoritario.",
            "measured": f"Acerto dinamico: {float(metrics['dynamic_only_family_accuracy']):.3f}; acerto topologico: {float(metrics['topology_only_family_accuracy']):.3f}.",
        },
        "edge_model_sensitivity.png": {
            "title_meaning": "Mostra se mudar o significado fisico da aresta muda o transporte.",
            "x_axis": "Modelo de aresta: igual para todas, normalizada por grau, decaimento por distancia etc.",
            "y_axis": "Familia de rede.",
            "color": "Cor mais clara significa melhor chegada media ao alvo.",
            "expected": "A literatura de CTQW espera que pesos e alcances alterem a dinamica porque mudam o Hamiltoniano.",
            "measured": "Este painel separa efeito de topologia do efeito de como a ligacao fisica e ponderada.",
        },
    }


def _write_summary(output_dir: Path, metrics: dict[str, object], classification_reports: dict[str, object]) -> None:
    acceptance = metrics["acceptance"]
    compact_reports = {
        key: {
            "accuracy": value["accuracy"],
            "baseline_accuracy": value["baseline_accuracy"],
            "labels": value["labels"],
            "top_features": value["feature_importance"][:5],
        }
        for key, value in classification_reports.items()
    }
    lines = [
        "# Transport methodological benchmarks",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        f"Profile: `{metrics['profile']}`",
        "",
        "## What was benchmarked",
        "",
        "- Closed coherent quantum-walk topology control.",
        "- Trap/target placement control.",
        "- Dephasing-assisted transport control.",
        "- Dynamic graph-family classification control.",
        "- Edge-weight model sensitivity control.",
        "",
        "## Main measured numbers",
        "",
        f"- Open dynamic signatures: {metrics['open_signature_count']}.",
        f"- Families: {', '.join(metrics['families'])}.",
        f"- Edge models: {', '.join(metrics['edge_models'])}.",
        f"- Largest dephasing gain: {float(metrics['largest_dephasing_gain']):.3f} in `{metrics['largest_dephasing_gain_family']}` / `{metrics['largest_dephasing_gain_target_style']}` / `{metrics['largest_dephasing_gain_edge_model']}`.",
        f"- Useful dephasing candidates: {metrics['useful_dephasing_candidate_count']}.",
        f"- Max target-position spread: {float(metrics['max_target_position_spread']):.3f}.",
        f"- Family classification, dynamic only: {float(metrics['dynamic_only_family_accuracy']):.3f}.",
        f"- Family classification, topology only: {float(metrics['topology_only_family_accuracy']):.3f}.",
        f"- Family classification, dynamic + topology: {float(metrics['combined_family_accuracy']):.3f}.",
        f"- Majority baseline: {float(metrics['family_baseline_accuracy']):.3f}.",
        "",
        "## Methodological verdict",
        "",
        f"- Numerics pass: {acceptance['numerics_pass']}.",
        f"- Target placement candidate: {acceptance['target_position_matters_candidate']}.",
        f"- Dephasing assistance candidate: {acceptance['dephasing_assistance_candidate']}.",
        f"- Dynamic classification above baseline: {acceptance['dynamic_classification_above_baseline']}.",
        f"- Dynamics adds beyond topology in this run: {acceptance['dynamics_adds_beyond_topology_candidate']}.",
        "",
        "## Important limitation",
        "",
        "This benchmark checks methodological coherence and reproduces qualitative expectations. It is not yet a final physics claim; article-level claims require the confirm profile and local refinement of the strongest cases.",
        "",
        "## Classification controls",
        "",
        "```json",
        json.dumps(compact_reports, indent=2, ensure_ascii=False),
        "```",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_latest(output_dir: Path, latest_dir: Path) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        target = latest_dir / path.name
        if path.is_file():
            target.write_bytes(path.read_bytes())
    latest_figures = latest_dir / "figures"
    latest_figures.mkdir(exist_ok=True)
    for path in (output_dir / "figures").iterdir():
        (latest_figures / path.name).write_bytes(path.read_bytes())


def run_benchmarks(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    closed_records, closed_series, closed_validation = _closed_walk_benchmark(config)
    open_records, example_series, open_validation = _build_open_scan_records(config)
    target_records = _target_position_benchmark(open_records)
    reports = _classification_reports(open_records)
    validation = {
        "max_trace_deviation": max(float(closed_validation["max_trace_deviation"]), float(open_validation["max_trace_deviation"])),
        "max_population_closure_error": max(float(closed_validation["max_population_closure_error"]), float(open_validation["max_population_closure_error"])),
        "min_state_eigenvalue": min(float(closed_validation["min_state_eigenvalue"]), float(open_validation["min_state_eigenvalue"])),
    }
    metrics = _benchmark_metrics(
        config=config,
        closed_records=closed_records,
        open_records=open_records,
        target_records=target_records,
        classification_reports=reports,
        validation=validation,
    )

    write_signature_csv(open_records, output_dir / "dynamic_signatures.csv")
    (output_dir / "benchmark_results.json").write_text(
        json.dumps(
            {
                "closed_walk_records": closed_records,
                "target_position_records": target_records,
                "open_records": open_records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "classification_reports.json").write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "profile": config["profile"]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    _write_methodology(output_dir, config)
    _write_summary(output_dir, metrics, reports)
    (output_dir / "plain_ptbr_explanations.json").write_text(json.dumps(_plain_ptbr_explanations(metrics), indent=2, ensure_ascii=False), encoding="utf-8")

    _plot_closed_return(closed_series, figures_dir / "closed_walk_return_probability.png")
    _plot_target_position(target_records, figures_dir / "trap_position_sensitivity.png")
    _plot_dephasing_gain(open_records, figures_dir / "dephasing_assistance_window.png")
    _plot_classification_controls(reports, figures_dir / "classification_controls.png")
    _plot_edge_sensitivity(open_records, figures_dir / "edge_model_sensitivity.png")
    strongest = max(open_records, key=lambda record: float(record["dephasing_gain"]))
    _plot_example_dynamics(example_series[str(strongest["record_id"])], figures_dir / "population_dynamics_strongest_gain.png")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run methodological benchmarks for dynamic open-transport network classification.")
    parser.add_argument("--profile", choices=["smoke", "interactive", "confirm"], default="smoke")
    parser.add_argument("--output-subdir", default="methodological_benchmarks")
    args = parser.parse_args(argv)
    config = _profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_benchmarks(config, output_dir)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
