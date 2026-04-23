from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
    SUPPORTED_DYNAMIC_NETWORK_FAMILIES,
    classification_result_to_dict,
    classify_records,
    generate_network_instance,
    numeric_feature_names,
    signature_from_dephasing_scan,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
    write_literature_guardrails,
    write_signature_csv,
)


LITERATURE_GUARDRAILS = [
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Moderate environmental action can improve transport when coherent motion is trapped by interference or disorder."},
    {"key": "PlenioHuelga2008", "url": "https://doi.org/10.1088/1367-2630/10/11/113019", "reading": "Dephasing can assist transport in networks, but excessive dephasing suppresses useful coherent motion."},
    {"key": "Rebentrost2009", "url": "https://doi.org/10.1088/1367-2630/11/3/033003", "reading": "Efficiency scans over disorder and dephasing are standard diagnostics for environment-assisted transport."},
    {"key": "Novo2016", "url": "https://doi.org/10.1038/srep18142", "reading": "Disorder can assist in suboptimal decoherence regimes, so ensemble statistics are necessary."},
    {"key": "Razzoli2021", "url": "https://doi.org/10.3390/e23010085", "reading": "Trap position and graph topology strongly affect continuous-time quantum-walk transport efficiency."},
    {"key": "Maier2019", "url": "https://doi.org/10.1103/PhysRevLett.122.050501", "reading": "Quantum simulators observe a progression from coherent dynamics to assistance and high-noise suppression."},
    {"key": "PerovskiteENAQT2025", "url": "https://www.nature.com/articles/s41467-024-55812-8", "reading": "Recent experiments support intermediate-regime transport where static disorder and dephasing compete."},
]


def _profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": profile,
            "families": ["chain", "ring", "complete", "star"],
            "n_sites_values": [6],
            "graph_realizations": 1,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 1000,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "dephasing_over_coupling": [0.0, 0.2],
            "target_styles": ["near", "far"],
            "t_final": 10.0,
            "n_time_samples": 90,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    if profile == "pilot":
        return {
            "profile": profile,
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 12,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23],
            "graph_seed_base": 2000,
            "disorder_strength_over_coupling": [0.0, 0.3, 0.6, 0.9, 1.2],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.8],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final": 16.0,
            "n_time_samples": 180,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    if profile == "confirm":
        return {
            "profile": profile,
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "n_sites_values": [12, 16, 20],
            "graph_realizations": 32,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137],
            "graph_seed_base": 3000,
            "disorder_strength_over_coupling": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2],
            "dephasing_over_coupling": [0.0, 0.03, 0.05, 0.08, 0.12, 0.2, 0.4, 0.8],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final": 18.0,
            "n_time_samples": 220,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _is_deterministic_family(family: str) -> bool:
    return family in {"chain", "ring", "complete", "star", "square_lattice_2d", "bottleneck", "clustered"}


def _record_numeric_subset(record: dict[str, object]) -> dict[str, float]:
    return {key: float(value) for key, value in record.items() if isinstance(value, (int, float, np.floating)) and np.isfinite(float(value))}


def _generate_records(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict[str, float]], dict[str, dict[str, object]], dict[str, object]]:
    records: list[dict[str, object]] = []
    topology_payload: dict[str, dict[str, float]] = {}
    example_series: dict[str, dict[str, object]] = {}
    validation = {
        "max_trace_deviation": 0.0,
        "max_population_closure_error": 0.0,
        "min_state_eigenvalue": 1.0,
    }
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    coupling_hz = float(config["coupling_hz"])
    dephasing_grid = np.asarray(config["dephasing_over_coupling"], dtype=float)
    disorder_grid = np.asarray(config["disorder_strength_over_coupling"], dtype=float)
    random_families = {"erdos_renyi", "watts_strogatz_small_world", "barabasi_albert_scale_free", "modular_two_community", "random_geometric"}

    for family in list(config["families"]):
        realization_count = int(config.get("deterministic_graph_realizations", 1)) if _is_deterministic_family(str(family)) else int(config["graph_realizations"])
        for n_sites in list(config["n_sites_values"]):
            for realization in range(realization_count):
                graph_seed = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * realization + len(records)
                if family not in random_families:
                    graph_seed = int(config["graph_seed_base"]) + int(n_sites) + realization
                instance = generate_network_instance(str(family), n_sites=int(n_sites), seed=graph_seed, realization_index=realization)
                initial_site = int(n_sites) - 1
                candidates = target_candidates(instance, initial_site=initial_site)
                for target_style in list(config["target_styles"]):
                    if target_style not in candidates:
                        continue
                    trap_site = int(candidates[target_style])
                    topo = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
                    topology_payload[f"{instance.instance_id}_{target_style}"] = topo
                    for disorder_strength in disorder_grid:
                        for disorder_seed in list(config["disorder_seeds"]):
                            seed = int(disorder_seed) + 17 * graph_seed + int(round(1000 * float(disorder_strength)))
                            site_energies = static_disorder_energies(int(n_sites), float(disorder_strength) * coupling_hz, seed=seed)
                            scan_results = [
                                simulate_transport(
                                    adjacency=instance.adjacency,
                                    coupling_hz=coupling_hz,
                                    dephasing_rate_hz=float(gamma) * coupling_hz,
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
                                coupling_hz=coupling_hz,
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
                            records.append(record)
                            best_index = int(np.argmax([result.transport_efficiency for result in scan_results]))
                            best_result = scan_results[best_index]
                            example_series[str(record["record_id"])] = {
                                "family": str(family),
                                "target_style": str(target_style),
                                "times": best_result.times.tolist(),
                                "node_populations": best_result.node_populations.tolist(),
                                "sink_population": best_result.sink_population.tolist(),
                                "loss_population": best_result.loss_population.tolist(),
                            }
                            validation["max_trace_deviation"] = max(float(validation["max_trace_deviation"]), float(record["max_trace_deviation"]))
                            validation["max_population_closure_error"] = max(float(validation["max_population_closure_error"]), float(record["max_population_closure_error"]))
                            validation["min_state_eigenvalue"] = min(float(validation["min_state_eigenvalue"]), float(record["min_state_eigenvalue"]))
    return records, topology_payload, example_series, validation


def _plot_family_heatmap(records: list[dict[str, object]], *, value_key: str, title: str, colorbar_label: str, output_path: Path) -> None:
    families = sorted({str(record["family"]) for record in records})
    disorder_values = sorted({float(record["disorder_strength_over_coupling"]) for record in records})
    matrix = np.zeros((len(families), len(disorder_values)), dtype=float)
    for row, family in enumerate(families):
        for col, disorder in enumerate(disorder_values):
            values = [float(record[value_key]) for record in records if str(record["family"]) == family and abs(float(record["disorder_strength_over_coupling"]) - disorder) < 1e-12]
            matrix[row, col] = float(np.mean(values)) if values else np.nan
    fig, ax = plt.subplots(figsize=(max(7.0, 0.75 * len(disorder_values) + 4), max(4.5, 0.35 * len(families) + 2.5)), constrained_layout=True)
    im = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_title(title)
    ax.set_xticks(np.arange(len(disorder_values)))
    ax.set_xticklabels([f"{value:.2f}" for value in disorder_values])
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    ax.set_xlabel("local irregularity / coherent coupling")
    ax.set_ylabel("network family")
    fig.colorbar(im, ax=ax, label=colorbar_label)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_embedding(report: dict[str, object], output_path: Path) -> None:
    points = list(report["embedding_2d"])
    families = sorted({str(point["family"]) for point in points})
    fig, ax = plt.subplots(figsize=(8.0, 6.0), constrained_layout=True)
    for family in families:
        xs = [float(point["x"]) for point in points if str(point["family"]) == family]
        ys = [float(point["y"]) for point in points if str(point["family"]) == family]
        ax.scatter(xs, ys, s=32, alpha=0.75, label=family)
    ax.set_title("2D embedding of dynamic transport signatures")
    ax.set_xlabel("signature component 1")
    ax.set_ylabel("signature component 2")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_confusion(report: dict[str, object], output_path: Path) -> None:
    labels = list(report["labels"])
    matrix = np.asarray(report["confusion_matrix"], dtype=float)
    fig, ax = plt.subplots(figsize=(7.2, 6.4), constrained_layout=True)
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_title("Classification confusion matrix")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("predicted family")
    ax.set_ylabel("true family")
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            ax.text(col, row, f"{int(matrix[row, col])}", ha="center", va="center", color="black")
    fig.colorbar(im, ax=ax, label="test records")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_feature_importance(report: dict[str, object], output_path: Path) -> None:
    items = list(report["feature_importance"])[:12]
    labels = [str(item["feature"]).replace("topology_", "topo: ") for item in items][::-1]
    values = [float(item["importance"]) for item in items][::-1]
    fig, ax = plt.subplots(figsize=(9.0, 6.0), constrained_layout=True)
    ax.barh(labels, values, color="#0f766e")
    ax.set_title("Most important features for topology classification")
    ax.set_xlabel("mean absolute logistic weight")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_example_dynamics(example: dict[str, object], output_path: Path, *, title_suffix: str) -> None:
    times = np.asarray(example["times"], dtype=float)
    populations = np.asarray(example["node_populations"], dtype=float)
    sink = np.asarray(example["sink_population"], dtype=float)
    loss = np.asarray(example["loss_population"], dtype=float)
    fig, ax = plt.subplots(figsize=(9.5, 5.5), constrained_layout=True)
    for site in range(populations.shape[1]):
        ax.plot(times, populations[:, site], lw=1.0, alpha=0.45)
    ax.plot(times, sink, color="#15803d", lw=2.6, label="target arrival")
    ax.plot(times, loss, color="#b91c1c", lw=2.0, label="loss")
    ax.set_title(f"Population dynamics example: {example['family']} / {example['target_style']} ({title_suffix})")
    ax.set_xlabel("time")
    ax.set_ylabel("population")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(
    output_dir: Path,
    *,
    config: dict[str, object],
    records: list[dict[str, object]],
    classification_report: dict[str, object],
    topology_only_report: dict[str, object],
    validation: dict[str, object],
    critic_report: dict[str, object],
) -> None:
    family_counts = Counter(str(record["family"]) for record in records)
    regime_counts = Counter(str(record["regime_label"]) for record in records)
    max_gain = max(float(record["dephasing_gain"]) for record in records)
    gain_records = [record for record in records if float(record["dephasing_gain"]) >= 0.05 and float(record["best_dephasing_over_coupling"]) > 0.0]
    best_gain = max(records, key=lambda record: float(record["dephasing_gain"]))
    lines = [
        "# Dynamic network classification campaign",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        f"Profile: `{config['profile']}`",
        "",
        "## What was tested",
        "",
        f"- Families: {', '.join(sorted(family_counts))}.",
        f"- Records: {len(records)} dynamic signatures.",
        f"- Disorder grid: {config['disorder_strength_over_coupling']}.",
        f"- Phase-scrambling grid: {config['dephasing_over_coupling']}.",
        "",
        "## What was measured",
        "",
        f"- Classification accuracy with topology + dynamics: {float(classification_report['accuracy']):.3f}.",
        f"- Classification accuracy with topology only: {float(topology_only_report['accuracy']):.3f}.",
        f"- Baseline majority accuracy: {float(classification_report['baseline_accuracy']):.3f}.",
        f"- Largest dephasing gain: {max_gain:.3f} in `{best_gain['family']}` with target `{best_gain['target_style']}`.",
        f"- Useful dephasing candidates with gain >= 0.05: {len(gain_records)}.",
        f"- Regime counts: {dict(regime_counts)}.",
        "",
        "## What the literature would expect",
        "",
        "- Dephasing can help when coherent motion is trapped by interference or disorder, but strong dephasing can suppress transport.",
        "- Target placement should matter in finite graphs and cannot be treated as a nuisance parameter.",
        "- Disorder requires ensemble statistics; single-seed behavior is not enough for a strong claim.",
        "",
        "## Current interpretation",
        "",
        "- If topology + dynamics beats topology-only classification, the time evolution carries information beyond static graph metrics.",
        "- If gains concentrate in specific families or target styles, the next campaign should refine those regions instead of expanding blindly.",
        "- This is not a material simulation; it is an effective model for classifying transport mechanisms in finite networks.",
        "",
        "## Critic report",
        "",
        f"- Level: {critic_report['level']}.",
        f"- Main concern: {critic_report['main_concern']}.",
        f"- Next action: {critic_report['next_action']}.",
        "",
        "## Numerical checks",
        "",
        f"- Max trace deviation: {float(validation['max_trace_deviation']):.3e}.",
        f"- Max population closure error: {float(validation['max_population_closure_error']):.3e}.",
        f"- Minimum state eigenvalue: {float(validation['min_state_eigenvalue']):.3e}.",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _critic_report(records: list[dict[str, object]], classification_report: dict[str, object], config: dict[str, object]) -> dict[str, object]:
    gain_candidates = [
        record
        for record in records
        if float(record["dephasing_gain"]) >= 0.05 and float(record["best_dephasing_over_coupling"]) > 0.0
    ]
    if str(config["profile"]) == "smoke":
        return {
            "level": "pilot_only",
            "main_concern": "Smoke run validates the pipeline but is too small for scientific claims.",
            "evidence": "Uses a tiny grid and few disorder seeds.",
            "next_action": "Run profile pilot for all network families, then refine only separable families.",
        }
    if float(classification_report["accuracy"]) <= float(classification_report["baseline_accuracy"]):
        return {
            "level": "warning",
            "main_concern": "Classifier did not beat majority baseline.",
            "evidence": "Dynamic signatures may be weak or feature scaling/grid may need revision.",
            "next_action": "Inspect feature importance and run C2 target placement before adding larger networks.",
        }
    if not gain_candidates:
        return {
            "level": "warning",
            "main_concern": "No useful dephasing candidates met the gain threshold.",
            "evidence": "No record had gain >= 0.05 with nonzero best phase scrambling.",
            "next_action": "Focus next campaign on target placement and disorder ranges before claiming noise as a tool.",
        }
    return {
        "level": "ok",
        "main_concern": "Claims still require ensemble confirmation before article-level language.",
        "evidence": f"{len(gain_candidates)} records met the useful dephasing candidate threshold.",
        "next_action": "Refine the strongest gain families with more disorder seeds and local gamma_phi grid.",
    }


def run_campaign(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    records, topology_payload, example_series, validation = _generate_records(config)
    feature_names = numeric_feature_names(records, include_dynamic=True)
    topology_feature_names = [name for name in feature_names if name.startswith("topology_")]
    classification = classification_result_to_dict(classify_records(records, feature_names=feature_names, label_name="family"))
    topology_only = classification_result_to_dict(classify_records(records, feature_names=topology_feature_names, label_name="family"))
    critic = _critic_report(records, classification, config)

    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    write_signature_csv(records, output_dir / "dynamic_signatures.csv")
    (output_dir / "results.json").write_text(json.dumps({"records": records}, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "topology_metrics.json").write_text(json.dumps(topology_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "classification_report.json").write_text(json.dumps(classification, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "topology_only_classification_report.json").write_text(json.dumps(topology_only, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "critic_report.json").write_text(json.dumps(critic, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "record_count": len(records)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)

    metrics = {
        "record_count": len(records),
        "families": sorted({str(record["family"]) for record in records}),
        "classification_accuracy": classification["accuracy"],
        "topology_only_accuracy": topology_only["accuracy"],
        "baseline_accuracy": classification["baseline_accuracy"],
        "max_dephasing_gain": max(float(record["dephasing_gain"]) for record in records),
        "useful_dephasing_candidate_count": sum(
            1
            for record in records
            if float(record["dephasing_gain"]) >= 0.05 and float(record["best_dephasing_over_coupling"]) > 0.0
        ),
        "validation": validation,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    _plot_family_heatmap(records, value_key="best_arrival", title="Mean target arrival by family and disorder", colorbar_label="best target arrival", output_path=figures_dir / "target_arrival_heatmap.png")
    _plot_family_heatmap(records, value_key="dephasing_gain", title="Mean dephasing gain by family and disorder", colorbar_label="best arrival minus zero-dephasing arrival", output_path=figures_dir / "dephasing_gain_heatmap.png")
    _plot_embedding(classification, figures_dir / "signature_embedding_2d.png")
    _plot_confusion(classification, figures_dir / "confusion_matrix.png")
    _plot_feature_importance(classification, figures_dir / "feature_importance.png")

    predictions_by_id = {str(item["record_id"]): item for item in classification["predictions"]}
    correct_id = next((record_id for record_id, pred in predictions_by_id.items() if pred["correct"] and record_id in example_series), next(iter(example_series)))
    wrong_id = next((record_id for record_id, pred in predictions_by_id.items() if not pred["correct"] and record_id in example_series), correct_id)
    _plot_example_dynamics(example_series[correct_id], figures_dir / "population_dynamics_correct_example.png", title_suffix="correct example")
    _plot_example_dynamics(example_series[wrong_id], figures_dir / "population_dynamics_wrong_or_hard_example.png", title_suffix="wrong or hard example")
    _write_summary(
        output_dir,
        config=config,
        records=records,
        classification_report=classification,
        topology_only_report=topology_only,
        validation=validation,
        critic_report=critic,
    )
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run dynamic network classification campaigns for open quantum transport.")
    parser.add_argument("--profile", choices=["smoke", "pilot", "confirm"], default="smoke")
    parser.add_argument("--output-subdir", default="dynamic_network_classification")
    args = parser.parse_args(argv)

    config = _profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_campaign(config, output_dir)
    latest_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        target = latest_dir / path.name
        if path.is_file():
            target.write_bytes(path.read_bytes())
    latest_figures = latest_dir / "figures"
    latest_figures.mkdir(exist_ok=True)
    for path in (output_dir / "figures").iterdir():
        (latest_figures / path.name).write_bytes(path.read_bytes())
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

