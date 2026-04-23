from __future__ import annotations

import argparse
import json
import sys
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
    DYNAMIC_SIGNATURE_FEATURES,
    aggregate_record_statistics,
    classification_result_to_dict,
    classify_records,
    classify_train_test_records,
    generate_network_instance,
    simulate_classical_transport,
    write_literature_guardrails,
    write_signature_csv,
    write_statistics_csv,
)
from scripts.run_transport_methodological_benchmarks import (  # noqa: E402
    LITERATURE_GUARDRAILS,
    _build_open_scan_records,
    _closed_walk_benchmark,
    _target_position_benchmark,
    _weighted_instance,
)


STATISTIC_METRICS = (
    "best_arrival",
    "dephasing_gain",
    "best_sink_hitting_time_filled",
    "best_mean_coherence_l1",
    "best_final_entropy",
    "best_participation_ratio",
    "best_ipr",
)


def _profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": profile,
            "families": ["erdos_renyi", "random_geometric"],
            "edge_models_main": ["unweighted"],
            "edge_models_sensitivity": ["unweighted", "exponential_distance"],
            "edge_sensitivity_families": ["random_geometric"],
            "n_sites_values": [6],
            "graph_realizations": 3,
            "deterministic_graph_realizations": 3,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 5100,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "dephasing_over_coupling": [0.0, 0.2, 0.6],
            "target_styles": ["near", "far"],
            "t_final_closed": 5.0,
            "t_final_open": 6.0,
            "n_time_samples": 42,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "n_repeats": 5,
        }
    if profile == "pilot":
        return {
            "profile": profile,
            "families": ["erdos_renyi", "watts_strogatz_small_world", "barabasi_albert_scale_free", "modular_two_community", "random_geometric"],
            "edge_models_main": ["unweighted"],
            "edge_models_sensitivity": ["unweighted", "exponential_distance"],
            "edge_sensitivity_families": ["random_geometric"],
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 8,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23],
            "graph_seed_base": 5200,
            "disorder_strength_over_coupling": [0.0, 0.3, 0.6, 0.9, 1.2],
            "dephasing_over_coupling": [0.0, 0.03, 0.05, 0.1, 0.2, 0.4, 0.8],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final_closed": 10.0,
            "t_final_open": 14.0,
            "n_time_samples": 150,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "n_repeats": 30,
        }
    if profile == "broad":
        return {
            "profile": profile,
            "families": [
                "chain",
                "ring",
                "star",
                "complete",
                "square_lattice_2d",
                "bottleneck",
                "clustered",
                "erdos_renyi",
                "watts_strogatz_small_world",
                "barabasi_albert_scale_free",
                "modular_two_community",
                "random_geometric",
            ],
            "edge_models_main": ["unweighted"],
            "edge_models_sensitivity": ["unweighted", "exponential_distance"],
            "edge_sensitivity_families": ["random_geometric", "ring", "modular_two_community"],
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 1,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 5250,
            "disorder_strength_over_coupling": [0.0, 0.6, 1.2],
            "dephasing_over_coupling": [0.0, 0.1, 0.4, 0.8],
            "target_styles": ["near", "far", "high_centrality"],
            "t_final_closed": 9.0,
            "t_final_open": 12.0,
            "n_time_samples": 72,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "n_repeats": 8,
        }
    if profile == "confirm":
        return {
            "profile": profile,
            "families": ["random_geometric"],
            "edge_models_main": ["exponential_distance"],
            "edge_models_sensitivity": ["exponential_distance"],
            "edge_sensitivity_families": ["random_geometric"],
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 24,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137],
            "graph_seed_base": 5300,
            "disorder_strength_over_coupling": [0.3, 0.5, 0.7, 0.9, 1.1, 1.3],
            "dephasing_over_coupling": [0.0, 0.03, 0.05, 0.08, 0.12, 0.2, 0.35, 0.6, 0.9],
            "target_styles": ["near"],
            "t_final_closed": 12.0,
            "t_final_open": 16.0,
            "n_time_samples": 180,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "n_repeats": 100,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _enrich_records(records: list[dict[str, object]]) -> None:
    for record in records:
        n_sites = int(round(float(record.get("topology_n_sites", 0.0))))
        record["n_sites"] = n_sites
        record["validation_group_id"] = f"{record['family']}_N{n_sites}_seed{record['graph_seed']}"


def _feature_sets(records: list[dict[str, object]]) -> dict[str, list[str]]:
    dynamic = [name for name in DYNAMIC_SIGNATURE_FEATURES if name in records[0]]
    topology = sorted([name for name in records[0] if name.startswith("topology_")])
    classical = [
        "classical_arrival",
        "classical_sink_hitting_time_filled",
        "classical_loss_population",
        "classical_network_population",
    ]
    difference = [
        "arrival_quantum_minus_classical",
        "hitting_time_quantum_minus_classical",
        "loss_quantum_minus_classical",
    ]
    return {
        "quantum_only": dynamic,
        "topology_only": topology,
        "classical_only": classical,
        "quantum_minus_classical": difference,
        "combined": dynamic + topology,
    }


def _classification_suite(records: list[dict[str, object]], *, split_strategy: str, n_repeats: int) -> dict[str, object]:
    if len({str(record["family"]) for record in records}) < 2:
        return {"not_applicable": "family classification needs at least two families"}
    features = _feature_sets(records)
    report: dict[str, object] = {}
    for name, feature_names in features.items():
        if not all(feature in records[0] for feature in feature_names):
            continue
        report[name] = classification_result_to_dict(
            classify_records(
                records,
                feature_names=feature_names,
                label_name="family",
                split_strategy=split_strategy,
                group_key="validation_group_id" if split_strategy == "group" else None,
                n_repeats=n_repeats,
                random_seed=17,
            )
        )
    return report


def _build_classical_control_records(records: list[dict[str, object]], config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    times = np.linspace(0.0, float(config["t_final_open"]), int(config["n_time_samples"]))
    cache: dict[tuple[object, ...], object] = {}
    enriched: list[dict[str, object]] = []
    max_closure = 0.0
    for record in records:
        n_sites = int(record["n_sites"])
        key = (
            record["family"],
            n_sites,
            int(record["graph_seed"]),
            record["edge_model"],
            int(record["initial_site"]),
            int(record["trap_site"]),
        )
        if key not in cache:
            base = generate_network_instance(str(record["family"]), n_sites=n_sites, seed=int(record["graph_seed"]), realization_index=0)
            instance = _weighted_instance(base, str(record["edge_model"]))
            cache[key] = simulate_classical_transport(
                instance.adjacency,
                hopping_rate_hz=float(config["coupling_hz"]),
                sink_rate_hz=float(config["sink_rate_hz"]),
                loss_rate_hz=float(config["loss_rate_hz"]),
                times=times,
                initial_site=int(record["initial_site"]),
                trap_site=int(record["trap_site"]),
                sink_hit_threshold=0.1,
                transfer_threshold=0.5,
            )
        classical = cache[key]
        max_closure = max(max_closure, float(classical.max_population_closure_error))
        filled_classical_hit = float(times[-1]) if classical.sink_hitting_time is None else float(classical.sink_hitting_time)
        row = dict(record)
        row["classical_arrival"] = float(classical.transport_efficiency)
        row["classical_sink_hitting_time_filled"] = filled_classical_hit
        row["classical_loss_population"] = float(classical.loss_population[-1])
        row["classical_network_population"] = float(classical.network_population[-1])
        row["arrival_quantum_minus_classical"] = float(row["best_arrival"]) - float(row["classical_arrival"])
        row["hitting_time_quantum_minus_classical"] = float(row["best_sink_hitting_time_filled"]) - filled_classical_hit
        row["loss_quantum_minus_classical"] = float(row["best_loss_population"]) - float(row["classical_loss_population"])
        enriched.append(row)
    return enriched, {
        "classical_cache_size": len(cache),
        "max_population_closure_error": max_closure,
        "mean_quantum_minus_classical_arrival": float(np.mean([row["arrival_quantum_minus_classical"] for row in enriched])),
    }


def _size_generalization_report(records: list[dict[str, object]]) -> dict[str, object]:
    if len({str(record["family"]) for record in records}) < 2:
        return {"not_applicable": "size generalization needs at least two families"}
    features = _feature_sets(records)
    report: dict[str, object] = {}
    train = [record for record in records if int(record["n_sites"]) == 8]
    for test_n in [10, 12]:
        test = [record for record in records if int(record["n_sites"]) == test_n]
        if not train or not test:
            report[f"train_N8_test_N{test_n}"] = {"not_applicable": "missing train or test size"}
            continue
        report[f"train_N8_test_N{test_n}"] = {
            name: classification_result_to_dict(classify_train_test_records(train, test, feature_names=feature_names, label_name="family"))
            for name, feature_names in features.items()
            if all(feature in records[0] for feature in feature_names)
        }
    return report


def _paper_reproduction_score(
    *,
    closed_records: list[dict[str, object]],
    target_records: list[dict[str, object]],
    records: list[dict[str, object]],
) -> dict[str, object]:
    matched: list[str] = []
    failed: list[str] = []
    uncertain: list[str] = []
    return_values = [float(row["long_time_average_return"]) for row in closed_records]
    if len(return_values) > 1 and float(np.std(return_values)) > 0.01:
        matched.append("Mulken/Blumen: closed-walk return probability depends on topology.")
    else:
        uncertain.append("Mulken/Blumen: topology dependence in closed-walk return was weak in this grid.")

    by_instance: dict[tuple[str, str], list[float]] = {}
    for row in target_records:
        by_instance.setdefault((str(row["family"]), str(row["instance_id"])), []).append(float(row["mean_zero_dephasing_arrival"]))
    target_spread = max((max(values) - min(values) for values in by_instance.values() if len(values) > 1), default=0.0)
    if target_spread >= 0.05:
        matched.append("Razzoli: target/trap placement changes transport efficiency.")
    else:
        failed.append("Razzoli: target/trap placement did not change efficiency above threshold.")

    gain_candidates = [row for row in records if float(row["dephasing_gain"]) >= 0.05 and float(row["best_dephasing_over_coupling"]) > 0.0]
    suppression_candidates = [row for row in gain_candidates if float(row["high_dephasing_penalty"]) > 0.02]
    if gain_candidates:
        matched.append("Mohseni/Plenio/Rebentrost: nonzero dephasing can improve target arrival.")
    else:
        failed.append("Mohseni/Plenio/Rebentrost: no dephasing-assisted candidate found.")
    if suppression_candidates:
        matched.append("Mohseni/Plenio/Rebentrost: high dephasing suppression appears after the optimum.")
    else:
        uncertain.append("Mohseni/Plenio/Rebentrost: high-noise suppression was not resolved in this grid.")

    return {
        "matched_expectation": matched,
        "failed_expectation": failed,
        "uncertain": uncertain,
        "thresholds": {
            "closed_return_std": 0.01,
            "target_spread": 0.05,
            "dephasing_gain": 0.05,
            "high_dephasing_penalty": 0.02,
        },
    }


def _plot_classification_reports(row_report: dict[str, object], group_report: dict[str, object], output_path: Path) -> None:
    labels = ["quantum_only", "classical_only", "topology_only", "combined"]
    row_values = [float(row_report.get(label, {}).get("accuracy_mean", 0.0)) for label in labels]
    group_values = [float(group_report.get(label, {}).get("accuracy_mean", 0.0)) for label in labels]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.8, 5.3), constrained_layout=True)
    ax.bar(x - 0.18, row_values, width=0.36, label="row split", color="#94a3b8")
    ax.bar(x + 0.18, group_values, width=0.36, label="group split", color="#2563eb")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("classification accuracy")
    ax.set_title("Classification honesty check")
    ax.legend(frameon=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_statistical_gain(rows: list[dict[str, object]], output_path: Path) -> None:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("family", "")), []).append(row)
    labels = sorted(grouped)
    means = [float(np.mean([float(row["dephasing_gain_mean"]) for row in grouped[label]])) for label in labels]
    errors = [float(np.mean([float(row["dephasing_gain_sem"]) for row in grouped[label]])) for label in labels]
    fig, ax = plt.subplots(figsize=(9.5, 5.5), constrained_layout=True)
    ax.bar(labels, means, yerr=errors, color="#0f766e", capsize=4)
    ax.axhline(0.05, color="#b91c1c", ls="--", lw=1.2, label="useful gain threshold")
    ax.set_title("Mean dephasing gain with uncertainty")
    ax.set_ylabel("best arrival minus zero-dephasing arrival")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(frameon=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_quantum_vs_classical(records: list[dict[str, object]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 6.0), constrained_layout=True)
    for family in sorted({str(row["family"]) for row in records}):
        values = [row for row in records if str(row["family"]) == family]
        ax.scatter(
            [float(row["classical_arrival"]) for row in values],
            [float(row["best_arrival"]) for row in values],
            s=26,
            alpha=0.65,
            label=family,
        )
    ax.plot([0, 1], [0, 1], color="#111827", ls="--", lw=1.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("classical target arrival")
    ax.set_ylabel("quantum/open target arrival")
    ax.set_title("Quantum/open transport versus classical rate control")
    ax.legend(frameon=False, fontsize=7)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_size_generalization(size_report: dict[str, object], output_path: Path) -> None:
    labels: list[str] = []
    values: list[float] = []
    for split_name, payload in size_report.items():
        if not isinstance(payload, dict) or "combined" not in payload:
            continue
        labels.append(split_name.replace("train_N8_test_", "test "))
        values.append(float(payload["combined"]["accuracy_mean"]))
    fig, ax = plt.subplots(figsize=(6.8, 4.8), constrained_layout=True)
    if values:
        ax.bar(labels, values, color="#7c2d12")
    else:
        ax.text(0.5, 0.5, "not enough sizes in this profile", ha="center", va="center")
        ax.set_xticks([])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("accuracy")
    ax.set_title("Size generalization: train N=8, test larger N")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _scientific_verdict(metrics: dict[str, object]) -> str:
    strong = (
        bool(metrics["numerics_pass"])
        and bool(metrics["group_split_beats_baseline"])
        and bool(metrics["classical_control_not_enough"])
        and bool(metrics["dephasing_ci_excludes_zero"])
        and bool(metrics["size_generalization_available"])
    )
    if strong:
        return "strong_candidate"
    if bool(metrics["group_split_beats_baseline"]) and bool(metrics["dephasing_ci_excludes_zero"]):
        return "promising_but_not_final"
    return "exploratory_only"


def _write_report(output_dir: Path, metrics: dict[str, object], paper_score: dict[str, object]) -> None:
    strongest = metrics.get("strongest_statistical_gain", {})
    if isinstance(strongest, dict) and strongest:
        next_candidate = (
            f"`{strongest.get('family', 'unknown')} + {strongest.get('edge_model', 'unknown')} + "
            f"{strongest.get('target_style', 'unknown')} target`"
        )
    else:
        next_candidate = "`strongest measured candidate`"
    lines = [
        "# Scientific validation report",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        f"Profile: `{metrics['profile']}`",
        "",
        "## Hypothesis",
        "",
        "Dynamic signatures of open quantum transport can classify finite network families and identify when dephasing helps or hurts target arrival.",
        "",
        "## Method",
        "",
        "- Row split is kept only as an optimistic/debugging control.",
        "- Group split is the scientific default: records from the same graph instance cannot appear in train and test at the same time.",
        "- A classical continuous-time rate model is run on the same graphs as a baseline.",
        "- Physical metrics are reported with mean, spread, standard error, and 95% confidence interval.",
        "",
        "## Main results",
        "",
        f"- Open signatures: {metrics['open_signature_count']}.",
        f"- Group-split combined accuracy: {float(metrics['group_combined_accuracy']):.3f}.",
        f"- Group-split baseline accuracy: {float(metrics['group_baseline_accuracy']):.3f}.",
        f"- Classical-only group accuracy: {float(metrics['group_classical_accuracy']):.3f}.",
        f"- Mean strongest dephasing gain: {float(metrics['max_gain_mean']):.3f}.",
        f"- Strong-effect criterion met: {metrics['strong_dephasing_effect_candidate']}.",
        f"- Scientific verdict: `{metrics['scientific_verdict']}`.",
        "",
        "## Paper reproduction score",
        "",
        f"- Matched: {paper_score['matched_expectation']}.",
        f"- Failed: {paper_score['failed_expectation']}.",
        f"- Uncertain: {paper_score['uncertain']}.",
        "",
        "## Limitations",
        "",
        "- This report does not turn the previous exploratory run into a final claim.",
        "- Confirmation requires the heavier profile if the smoke/pilot result remains promising.",
        "- A result is not called quantum-specific unless it beats the classical control under group split.",
        "",
        "## Next recommended campaign",
        "",
        f"Refine {next_candidate} with the confirm profile only if group-split and classical-control criteria remain positive in pilot mode.",
    ]
    (output_dir / "scientific_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _strong_dephasing_candidate(stat_rows: list[dict[str, object]]) -> tuple[bool, dict[str, object]]:
    candidates = [
        row
        for row in stat_rows
        if float(row.get("dephasing_gain_mean", 0.0)) >= 0.05
        and float(row.get("dephasing_gain_ci95_low", 0.0)) > 0.0
        and float(row.get("best_dephasing_over_coupling", 0.0)) > 0.0
    ]
    if not candidates:
        return False, {}
    by_context: dict[tuple[str, str, str], list[float]] = {}
    for row in candidates:
        key = (str(row.get("family", "")), str(row.get("edge_model", "")), str(row.get("target_style", "")))
        by_context.setdefault(key, []).append(float(row.get("disorder_strength_over_coupling", 0.0)))
    persistent = any(len(set(values)) >= 2 for values in by_context.values())
    strongest = max(candidates, key=lambda row: float(row.get("dephasing_gain_mean", 0.0)))
    return bool(persistent), strongest


def run_validation(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    closed_records, closed_series, closed_validation = _closed_walk_benchmark(config)
    open_records, _, open_validation = _build_open_scan_records(config)
    _enrich_records(open_records)
    target_records = _target_position_benchmark(open_records)
    classical_records, classical_control = _build_classical_control_records(open_records, config)

    stat_rows = aggregate_record_statistics(
        classical_records,
        group_keys=("family", "edge_model", "target_style", "disorder_strength_over_coupling", "best_dephasing_over_coupling"),
        metric_keys=STATISTIC_METRICS,
    )
    strong_dephasing, strongest_stat = _strong_dephasing_candidate(stat_rows)

    n_repeats = int(config["n_repeats"])
    row_report = _classification_suite(classical_records, split_strategy="row", n_repeats=min(5, n_repeats))
    group_report = _classification_suite(classical_records, split_strategy="group", n_repeats=n_repeats)
    size_report = _size_generalization_report(classical_records)
    paper_score = _paper_reproduction_score(closed_records=closed_records, target_records=target_records, records=classical_records)

    group_combined = group_report.get("combined", {}) if isinstance(group_report, dict) else {}
    group_classical = group_report.get("classical_only", {}) if isinstance(group_report, dict) else {}
    group_quantum = group_report.get("quantum_only", {}) if isinstance(group_report, dict) else {}
    group_delta = group_report.get("quantum_minus_classical", {}) if isinstance(group_report, dict) else {}
    group_combined_accuracy = float(group_combined.get("accuracy_mean", 0.0))
    group_baseline_accuracy = float(group_combined.get("baseline_accuracy", 0.0))
    group_classical_accuracy = float(group_classical.get("accuracy_mean", 0.0))
    group_quantum_accuracy = float(group_quantum.get("accuracy_mean", 0.0))
    group_delta_accuracy = float(group_delta.get("accuracy_mean", 0.0))
    size_available = any(isinstance(value, dict) and "combined" in value for value in size_report.values())
    validation = {
        "max_trace_deviation": max(float(closed_validation["max_trace_deviation"]), float(open_validation["max_trace_deviation"])),
        "max_population_closure_error": max(float(closed_validation["max_population_closure_error"]), float(open_validation["max_population_closure_error"])),
        "min_state_eigenvalue": min(float(closed_validation["min_state_eigenvalue"]), float(open_validation["min_state_eigenvalue"])),
        "classical_max_population_closure_error": float(classical_control["max_population_closure_error"]),
    }
    numerics_pass = bool(
        validation["max_trace_deviation"] < 1e-8
        and validation["max_population_closure_error"] < 1e-8
        and validation["min_state_eigenvalue"] > -1e-7
        and validation["classical_max_population_closure_error"] < 1e-8
    )
    metrics = {
        "profile": config["profile"],
        "open_signature_count": len(open_records),
        "statistical_rows": len(stat_rows),
        "families": sorted({str(record["family"]) for record in classical_records}),
        "edge_models": sorted({str(record["edge_model"]) for record in classical_records}),
        "validation": validation,
        "numerics_pass": numerics_pass,
        "group_combined_accuracy": group_combined_accuracy,
        "group_baseline_accuracy": group_baseline_accuracy,
        "group_classical_accuracy": group_classical_accuracy,
        "group_quantum_accuracy": group_quantum_accuracy,
        "group_delta_accuracy": group_delta_accuracy,
        "group_split_beats_baseline": bool(group_combined_accuracy > group_baseline_accuracy),
        "classical_control_not_enough": bool(max(group_quantum_accuracy, group_delta_accuracy) > group_classical_accuracy + 0.02),
        "dephasing_ci_excludes_zero": bool(strong_dephasing),
        "strong_dephasing_effect_candidate": bool(strong_dephasing),
        "strongest_statistical_gain": strongest_stat,
        "max_gain_mean": float(strongest_stat.get("dephasing_gain_mean", 0.0)) if strongest_stat else 0.0,
        "size_generalization_available": bool(size_available),
        "classical_control": classical_control,
    }
    metrics["scientific_verdict"] = _scientific_verdict(metrics)

    write_signature_csv(classical_records, output_dir / "dynamic_signatures_with_classical.csv")
    write_statistics_csv(stat_rows, output_dir / "statistical_summary.csv")
    (output_dir / "statistical_summary.json").write_text(json.dumps({"rows": stat_rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "benchmark_records.json").write_text(
        json.dumps(
            {
                "closed_walk_records": closed_records,
                "target_position_records": target_records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "row_split_report.json").write_text(json.dumps(row_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "group_split_report.json").write_text(json.dumps(group_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "classical_control_report.json").write_text(json.dumps(classical_control, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "size_generalization_report.json").write_text(json.dumps(size_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "paper_reproduction_score.json").write_text(json.dumps(paper_score, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "profile": config["profile"]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    _write_report(output_dir, metrics, paper_score)

    from scripts.run_transport_methodological_benchmarks import _plot_closed_return, _plot_target_position

    _plot_closed_return(closed_series, figures_dir / "closed_walk_benchmark.png")
    _plot_target_position(target_records, figures_dir / "target_placement_with_controls.png")
    _plot_statistical_gain(stat_rows, figures_dir / "dephasing_gain_with_ci.png")
    _plot_quantum_vs_classical(classical_records, figures_dir / "quantum_vs_classical_arrival.png")
    _plot_classification_reports(row_report, group_report, figures_dir / "classification_group_vs_row.png")
    _plot_size_generalization(size_report, figures_dir / "size_generalization.png")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run scientific validation for dynamic open-transport network classification.")
    parser.add_argument("--profile", choices=["smoke", "broad", "pilot", "confirm"], default="smoke")
    parser.add_argument("--output-subdir", default="scientific_validation")
    args = parser.parse_args(argv)
    config = _profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_validation(config, output_dir)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
