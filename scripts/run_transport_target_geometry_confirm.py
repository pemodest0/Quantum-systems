from __future__ import annotations

import argparse
import csv
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
    topology_metrics,
)
from scripts.run_transport_methodological_benchmarks import _weighted_instance  # noqa: E402


FAMILIES = ("chain", "ring", "modular_two_community", "random_geometric")


def profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": "smoke",
            "n_sites_values": [8],
            "graph_realizations": 1,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "disorder_seeds": [3],
            "dephasing_over_coupling": [0.0, 0.8],
            "t_final": 7.0,
            "n_time_samples": 52,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "graph_seed_base": 9100,
        }
    if profile == "interactive":
        return {
            "profile": "interactive",
            "n_sites_values": [8, 10],
            "graph_realizations": 2,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "disorder_seeds": [3, 5],
            "dephasing_over_coupling": [0.0, 0.8, 1.4],
            "t_final": 8.0,
            "n_time_samples": 64,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "graph_seed_base": 9200,
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


def _all_target_candidates(instance) -> dict[str, int]:
    graph = graph_from_adjacency(instance.adjacency)
    return {f"site_{node}": int(node) for node in range(graph.number_of_nodes() - 1)}


def _controlled_pair_labels(items: list[dict[str, object]]) -> tuple[str, str, str]:
    pairs: list[tuple[float, float, dict[str, object], dict[str, object]]] = []
    for i, left in enumerate(items):
        for right in items[i + 1 :]:
            arrival_delta = abs(float(left["arrival"]) - float(right["arrival"]))
            distance_delta = abs(float(left["topology_initial_target_distance"]) - float(right["topology_initial_target_distance"]))
            centrality_delta = abs(float(left["topology_target_closeness"]) - float(right["topology_target_closeness"]))
            pairs.append((arrival_delta, distance_delta, left, right))
            pairs.append((arrival_delta, centrality_delta, left, right))
    if not pairs:
        label = str(items[0]["target_label"]) if items else ""
        return label, label, "no_pair"
    similar_distance = min(
        pairs,
        key=lambda item: (item[1] if abs(float(item[2]["topology_initial_target_distance"]) - float(item[3]["topology_initial_target_distance"])) <= 1.0 else 999.0, -item[0]),
    )
    similar_centrality = min(
        pairs,
        key=lambda item: (abs(float(item[2]["topology_target_closeness"]) - float(item[3]["topology_target_closeness"])), -item[0]),
    )
    return (
        f"{similar_distance[2]['target_label']}__vs__{similar_distance[3]['target_label']}",
        f"{similar_centrality[2]['target_label']}__vs__{similar_centrality[3]['target_label']}",
        "selected",
    )


def _simulate_best_for_target(
    *,
    instance,
    config: dict[str, object],
    times: np.ndarray,
    initial_site: int,
    trap_site: int,
    target_label: str,
    n_sites: int,
    graph_seed: int,
    realization: int,
    disorder: float,
    disorder_seed: int,
) -> tuple[dict[str, object], dict[str, float]]:
    coupling = float(config["coupling_hz"])
    seed = int(disorder_seed) + 17 * int(graph_seed) + int(round(1000 * float(disorder)))
    site_energies = static_disorder_energies(int(n_sites), float(disorder) * coupling, seed=seed)
    topo = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
    best: dict[str, object] | None = None
    zero_arrival = 0.0
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
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
        row: dict[str, object] = {
            "family": instance.family,
            "n_sites": int(n_sites),
            "instance_id": instance.instance_id,
            "graph_seed": int(graph_seed),
            "realization": int(realization),
            "disorder_strength_over_coupling": float(disorder),
            "disorder_seed": int(disorder_seed),
            "target_label": target_label,
            "trap_site": int(trap_site),
            "initial_site": int(initial_site),
            "arrival": float(result.transport_efficiency),
            "dephasing_over_coupling": float(gamma),
            "sink_hitting_time_filled": float(result.times[-1]) if result.sink_hitting_time is None else float(result.sink_hitting_time),
            "loss_population": float(result.loss_population[-1]),
            "mean_coherence_l1": float(result.mean_coherence_l1),
            "final_entropy": float(result.final_entropy),
            "participation_ratio": float(result.final_participation_ratio),
        }
        row.update({f"topology_{key}": float(value) for key, value in topo.items()})
        if best is None or float(row["arrival"]) > float(best["arrival"]):
            best = row
        validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(result.max_trace_deviation))
        validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(result.max_population_closure_error))
        validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(result.min_state_eigenvalue))
    assert best is not None
    best["zero_dephasing_arrival"] = zero_arrival
    best["dephasing_gain"] = float(best["arrival"]) - zero_arrival
    return best, validation


def _quantum_classical_row(row: dict[str, object], instance, config: dict[str, object], times: np.ndarray) -> tuple[dict[str, object], float]:
    classical = simulate_classical_transport(
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
    delta = float(row["arrival"]) - float(classical.transport_efficiency)
    if float(row["arrival"]) < 0.1 and float(classical.transport_efficiency) < 0.1:
        label = "both_poor"
    elif delta > 0.05:
        label = "quantum_advantage_like"
    elif abs(delta) <= 0.05:
        label = "classical_explains"
    else:
        label = "inconclusive"
    return (
        {
            "family": row["family"],
            "n_sites": row["n_sites"],
            "target_label": row["target_label"],
            "arrival_quantum": row["arrival"],
            "arrival_classical": float(classical.transport_efficiency),
            "arrival_delta_quantum_minus_classical": delta,
            "quantum_hitting_time": row["sink_hitting_time_filled"],
            "classical_hitting_time": float(times[-1]) if classical.sink_hitting_time is None else float(classical.sink_hitting_time),
            "comparison_label": label,
        },
        float(classical.max_population_closure_error),
    )


def run_campaign(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    target_records: list[dict[str, object]] = []
    qc_rows: list[dict[str, object]] = []
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0, "classical_max_population_closure_error": 0.0}

    for family in FAMILIES:
        random_family = family in {"modular_two_community", "random_geometric"}
        for n_sites in list(config["n_sites_values"]):
            realization_count = int(config["graph_realizations"]) if random_family else 1
            for realization in range(realization_count):
                graph_seed = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * realization + len(target_records)
                if not random_family:
                    graph_seed = int(config["graph_seed_base"]) + int(n_sites)
                instance = _weighted_instance(generate_network_instance(family, n_sites=int(n_sites), seed=graph_seed, realization_index=realization), "unweighted")
                initial_site = int(n_sites) - 1
                target_labels = _all_target_candidates(instance)
                for disorder in list(config["disorder_strength_over_coupling"]):
                    for disorder_seed in list(config["disorder_seeds"]):
                        local_rows = []
                        for target_label, trap_site in target_labels.items():
                            row, val = _simulate_best_for_target(
                                instance=instance,
                                config=config,
                                times=times,
                                initial_site=initial_site,
                                trap_site=int(trap_site),
                                target_label=target_label,
                                n_sites=int(n_sites),
                                graph_seed=graph_seed,
                                realization=realization,
                                disorder=float(disorder),
                                disorder_seed=int(disorder_seed),
                            )
                            local_rows.append(row)
                            validation["max_trace_deviation"] = max(validation["max_trace_deviation"], val["max_trace_deviation"])
                            validation["max_population_closure_error"] = max(validation["max_population_closure_error"], val["max_population_closure_error"])
                            validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], val["min_state_eigenvalue"])
                            qc_row, closure = _quantum_classical_row(row, instance, config, times)
                            qc_rows.append(qc_row)
                            validation["classical_max_population_closure_error"] = max(validation["classical_max_population_closure_error"], closure)
                        target_records.extend(local_rows)

    pair_rows, controlled_rows = _pair_summaries(target_records)
    _write_csv(target_records, output_dir / "target_all_sites_records.csv")
    _write_csv(pair_rows, output_dir / "target_pair_confirmations.csv")
    _write_csv(controlled_rows, output_dir / "controlled_pair_tests.csv")
    _write_csv(qc_rows, output_dir / "quantum_classical_target_controls.csv")
    _write_summary(output_dir, pair_rows, controlled_rows, qc_rows, validation)
    _plot_pair_contrasts(pair_rows, figures_dir / "target_pair_contrasts.png")
    _plot_controlled_pairs(controlled_rows, figures_dir / "controlled_pair_tests.png")
    _plot_qc(qc_rows, figures_dir / "quantum_classical_target_controls.png")
    metrics = _metrics(pair_rows, controlled_rows, qc_rows, validation, config)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat()}, indent=2, ensure_ascii=False), encoding="utf-8")
    return metrics


def _pair_summaries(records: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in records:
        grouped[(str(row["family"]), str(row["n_sites"]), str(row["graph_seed"]), str(row["disorder_strength_over_coupling"]), str(row["disorder_seed"]))].append(row)
    pair_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    controlled_rows: list[dict[str, object]] = []
    for context, items in grouped.items():
        if len(items) < 2:
            continue
        best = max(items, key=lambda row: float(row["arrival"]))
        worst = min(items, key=lambda row: float(row["arrival"]))
        pair_values[(str(best["family"]), "best_vs_worst")].append(float(best["arrival"]) - float(worst["arrival"]))
        distance_pair = _best_control_pair(items, mode="similar_distance")
        centrality_pair = _best_control_pair(items, mode="similar_centrality")
        for mode, pair in [("similar_distance", distance_pair), ("similar_centrality", centrality_pair)]:
            left, right = pair
            controlled_rows.append(
                {
                    "family": context[0],
                    "n_sites": context[1],
                    "graph_seed": context[2],
                    "control_mode": mode,
                    "left_target": left["target_label"],
                    "right_target": right["target_label"],
                    "arrival_delta": abs(float(left["arrival"]) - float(right["arrival"])),
                    "distance_delta": abs(float(left["topology_initial_target_distance"]) - float(right["topology_initial_target_distance"])),
                    "centrality_delta": abs(float(left["topology_target_closeness"]) - float(right["topology_target_closeness"])),
                    "degree_delta": abs(float(left["topology_target_degree"]) - float(right["topology_target_degree"])),
                }
            )
    pair_rows = []
    for (family, pair_type), values in sorted(pair_values.items()):
        summary = mean_std_sem_ci95(values)
        verdict = "target_confirmed" if float(summary["ci95_low"]) > 0.05 else "inconclusive"
        pair_rows.append(
            {
                "family": family,
                "pair_type": pair_type,
                "n": summary["n"],
                "arrival_spread_mean": summary["mean"],
                "arrival_spread_ci95_low": summary["ci95_low"],
                "arrival_spread_ci95_high": summary["ci95_high"],
                "verdict": verdict,
            }
        )
    return pair_rows, controlled_rows


def _best_control_pair(items: list[dict[str, object]], *, mode: str) -> tuple[dict[str, object], dict[str, object]]:
    candidates = []
    for i, left in enumerate(items):
        for right in items[i + 1 :]:
            arrival_delta = abs(float(left["arrival"]) - float(right["arrival"]))
            distance_delta = abs(float(left["topology_initial_target_distance"]) - float(right["topology_initial_target_distance"]))
            centrality_delta = abs(float(left["topology_target_closeness"]) - float(right["topology_target_closeness"]))
            if mode == "similar_distance":
                score = (distance_delta, -arrival_delta)
            else:
                score = (centrality_delta, -arrival_delta)
            candidates.append((score, left, right))
    _, left, right = min(candidates, key=lambda item: item[0])
    return left, right


def _metrics(pair_rows: list[dict[str, object]], controlled_rows: list[dict[str, object]], qc_rows: list[dict[str, object]], validation: dict[str, float], config: dict[str, object]) -> dict[str, object]:
    qc_values = [float(row["arrival_delta_quantum_minus_classical"]) for row in qc_rows]
    counts = defaultdict(int)
    for row in qc_rows:
        counts[str(row["comparison_label"])] += 1
    numerics_pass = bool(
        validation["max_trace_deviation"] < 1e-8
        and validation["max_population_closure_error"] < 1e-8
        and validation["min_state_eigenvalue"] > -1e-7
        and validation["classical_max_population_closure_error"] < 1e-8
    )
    return {
        "profile": config["profile"],
        "pair_rows": len(pair_rows),
        "controlled_pair_rows": len(controlled_rows),
        "quantum_classical_rows": len(qc_rows),
        "validation": validation,
        "numerics_pass": numerics_pass,
        "confirmed_family_count": sum(1 for row in pair_rows if row["verdict"] == "target_confirmed"),
        "mean_quantum_classical_delta": float(np.mean(qc_values)) if qc_values else 0.0,
        "quantum_advantage_like_count": int(counts["quantum_advantage_like"]),
        "classical_explains_count": int(counts["classical_explains"]),
    }


def _write_summary(output_dir: Path, pair_rows: list[dict[str, object]], controlled_rows: list[dict[str, object]], qc_rows: list[dict[str, object]], validation: dict[str, float]) -> None:
    best = max(pair_rows, key=lambda row: float(row["arrival_spread_mean"])) if pair_rows else {}
    qc_values = [float(row["arrival_delta_quantum_minus_classical"]) for row in qc_rows]
    lines = [
        "# Target Geometry Confirmation",
        "",
        "## Main reading",
        "",
        f"- Strongest target spread: `{float(best.get('arrival_spread_mean', 0.0)):.3f}` in `{best.get('family', 'unknown')}`.",
        f"- Confirmed families: `{sum(1 for row in pair_rows if row['verdict'] == 'target_confirmed')}`.",
        f"- Mean quantum-classical arrival delta: `{float(np.mean(qc_values)) if qc_values else 0.0:.3f}`.",
        f"- Numerical closure: `{validation}`.",
        "",
        "A target effect is accepted only when the CI95 lower bound of target spread is above `0.05`.",
        "",
    ]
    output_dir.joinpath("summary.md").write_text("\n".join(lines), encoding="utf-8")


def _plot_pair_contrasts(rows: list[dict[str, object]], path: Path) -> None:
    labels = [str(row["family"]) for row in rows]
    means = [float(row["arrival_spread_mean"]) for row in rows]
    low = [float(row["arrival_spread_ci95_low"]) for row in rows]
    high = [float(row["arrival_spread_ci95_high"]) for row in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    ax.bar(x, means, color="#1565c0")
    ax.errorbar(x, means, yerr=[np.asarray(means) - np.asarray(low), np.asarray(high) - np.asarray(means)], fmt="none", ecolor="black", capsize=4)
    ax.axhline(0.05, color="#c62828", ls="--", lw=1, label="claim threshold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("best-worst target arrival spread")
    ax.set_title("Target placement confirmation")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_controlled_pairs(rows: list[dict[str, object]], path: Path) -> None:
    modes = sorted({str(row["control_mode"]) for row in rows})
    means = [float(np.mean([float(row["arrival_delta"]) for row in rows if row["control_mode"] == mode])) for mode in modes]
    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    ax.bar(modes, means, color="#2e7d32")
    ax.axhline(0.05, color="#c62828", ls="--", lw=1)
    ax.set_ylabel("mean arrival difference")
    ax.set_title("Controlled target pairs")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_qc(rows: list[dict[str, object]], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 5.4), constrained_layout=True)
    ax.scatter([float(row["arrival_classical"]) for row in rows], [float(row["arrival_quantum"]) for row in rows], s=16, alpha=0.6)
    ax.plot([0, 1], [0, 1], color="black", ls="--", lw=1)
    ax.set_xlabel("classical arrival")
    ax.set_ylabel("open-quantum arrival")
    ax.set_title("Target-confirmation quantum vs classical control")
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=220)
    plt.close(fig)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Confirm target-position effects and quantum/classical controls.")
    parser.add_argument("--profile", choices=["smoke", "interactive"], default="smoke")
    parser.add_argument("--output-subdir", default="target_geometry_confirm")
    args = parser.parse_args(argv)
    config = profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_campaign(config, output_dir)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
