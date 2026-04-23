from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
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
    aggregate_paper_verdicts,
    estimate_msd_exponent,
    evaluate_paper_claims,
    generate_network_instance,
    paper_claim_to_dict,
    simulate_transport,
    solve_effective_source_drain_steady_state,
    static_disorder_energies,
    target_candidates,
)
from scripts.run_transport_methodological_benchmarks import (  # noqa: E402
    _is_deterministic_family,
    _weighted_instance,
)
from scripts.run_transport_scientific_validation import (  # noqa: E402
    _profile_config as _validation_profile_config,
    run_validation,
)


VERDICT_COLORS = {
    "matched": "#2e7d32",
    "diverged": "#c62828",
    "inconclusive": "#f9a825",
    "not_applicable": "#607d8b",
}


def _confirm_profile_config() -> dict[str, object]:
    return {
        "profile": "confirm",
        "families": ["modular_two_community"],
        "edge_models_main": ["unweighted"],
        "edge_models_sensitivity": ["unweighted"],
        "edge_sensitivity_families": ["modular_two_community"],
        "n_sites_values": [8, 10, 12],
        "graph_realizations": 8,
        "deterministic_graph_realizations": 1,
        "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41],
        "graph_seed_base": 6200,
        "disorder_strength_over_coupling": [0.6, 0.9, 1.2, 1.5],
        "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.2],
        "target_styles": ["near"],
        "t_final_closed": 12.0,
        "t_final_open": 16.0,
        "n_time_samples": 120,
        "coupling_hz": 1.0,
        "sink_rate_hz": 0.65,
        "loss_rate_hz": 0.02,
        "n_repeats": 40,
    }


def profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return _validation_profile_config("smoke")
    if profile == "paper":
        config = _validation_profile_config("broad")
        config["profile"] = "paper"
        return config
    if profile == "confirm":
        return _confirm_profile_config()
    raise ValueError(f"Unsupported paper reproduction profile: {profile}")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_records_csv(records: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for record in records for key in record})
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fields})


def _auxiliary_profile_config(config: dict[str, object]) -> dict[str, object]:
    profile = str(config["profile"])
    if profile == "smoke":
        return {
            "n_sites_values": [6],
            "graph_realizations": 1,
            "disorder_seeds": [3],
            "coates_families": ["ring"],
            "coates_disorder": [0.6],
            "coates_gamma": [0.0, 0.2, 0.6],
            "anderson_families": ["chain", "ring"],
            "anderson_disorder": [0.0, 1.0],
            "steady_families": ["chain"],
        }
    if profile == "confirm":
        return {
            "n_sites_values": [8, 10],
            "graph_realizations": 4,
            "disorder_seeds": [3, 5, 7, 11],
            "coates_families": ["modular_two_community", "random_geometric", "bottleneck", "ring"],
            "coates_disorder": [0.3, 0.6, 0.9, 1.2],
            "coates_gamma": [0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.3, 1.6],
            "anderson_families": ["chain", "ring", "square_lattice_2d", "random_geometric"],
            "anderson_disorder": [0.0, 0.5, 1.0, 1.5, 2.0],
            "steady_families": ["chain", "ring", "square_lattice_2d"],
        }
    return {
        "n_sites_values": [8],
        "graph_realizations": 2,
        "disorder_seeds": [3, 5],
        "coates_families": ["modular_two_community", "random_geometric", "bottleneck", "ring"],
        "coates_disorder": [0.3, 0.6, 0.9, 1.2],
        "coates_gamma": [0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.3, 1.6],
        "anderson_families": ["chain", "ring", "square_lattice_2d", "random_geometric"],
        "anderson_disorder": [0.0, 0.5, 1.0, 1.5, 2.0],
        "steady_families": ["chain", "ring", "square_lattice_2d"],
    }


def _realization_count(family: str, aux: dict[str, object]) -> int:
    return 1 if _is_deterministic_family(family) else int(aux["graph_realizations"])


def _instance_for_auxiliary(family: str, n_sites: int, seed: int, realization: int):
    base = generate_network_instance(family, n_sites=n_sites, seed=seed, realization_index=realization)
    return _weighted_instance(base, "unweighted")


def _run_gamma_resolved_curves(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, float]]:
    aux = _auxiliary_profile_config(config)
    rows: list[dict[str, object]] = []
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final_open"]), int(config["n_time_samples"]))
    for family in list(aux["coates_families"]):
        family = str(family)
        for n_sites in list(aux["n_sites_values"]):
            n_sites = int(n_sites)
            for realization in range(_realization_count(family, aux)):
                graph_seed = int(config["graph_seed_base"]) + 44_000 + 1000 * n_sites + 97 * realization + len(rows)
                instance = _instance_for_auxiliary(family, n_sites, graph_seed, realization)
                initial_site = n_sites - 1
                candidates = target_candidates(instance, initial_site=initial_site)
                trap_site = int(candidates.get("near", candidates.get("far", 0)))
                for disorder_strength in list(aux["coates_disorder"]):
                    for disorder_seed in list(aux["disorder_seeds"]):
                        seed = int(disorder_seed) + 23 * graph_seed + int(round(1000 * float(disorder_strength)))
                        site_energies = static_disorder_energies(
                            n_sites,
                            float(disorder_strength) * float(config["coupling_hz"]),
                            seed=seed,
                        )
                        for gamma in list(aux["coates_gamma"]):
                            result = simulate_transport(
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
                            )
                            rows.append(
                                {
                                    "paper_key": "coates_2023",
                                    "family": family,
                                    "n_sites": n_sites,
                                    "instance_id": instance.instance_id,
                                    "graph_seed": graph_seed,
                                    "target_style": "near",
                                    "initial_site": initial_site,
                                    "trap_site": trap_site,
                                    "disorder_seed": int(disorder_seed),
                                    "disorder_strength_over_coupling": float(disorder_strength),
                                    "dephasing_over_coupling": float(gamma),
                                    "arrival": result.transport_efficiency,
                                    "entropy": result.final_entropy,
                                    "coherence": result.mean_coherence_l1,
                                    "loss": float(result.loss_population[-1]),
                                }
                            )
                            validation["max_trace_deviation"] = max(validation["max_trace_deviation"], result.max_trace_deviation)
                            validation["max_population_closure_error"] = max(validation["max_population_closure_error"], result.max_population_closure_error)
                            validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], result.min_state_eigenvalue)
    return rows, validation


def _run_localization_disorder_benchmark(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, float]]:
    aux = _auxiliary_profile_config(config)
    rows: list[dict[str, object]] = []
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final_closed"]), int(config["n_time_samples"]))
    for family in list(aux["anderson_families"]):
        family = str(family)
        for n_sites in list(aux["n_sites_values"]):
            n_sites = int(n_sites)
            for realization in range(_realization_count(family, aux)):
                graph_seed = int(config["graph_seed_base"]) + 55_000 + 1000 * n_sites + 83 * realization + len(rows)
                instance = _instance_for_auxiliary(family, n_sites, graph_seed, realization)
                initial_site = n_sites - 1
                candidates = target_candidates(instance, initial_site=initial_site)
                target_site = int(candidates.get("far", candidates.get("near", 0)))
                for disorder_strength in list(aux["anderson_disorder"]):
                    seed_values = list(aux["disorder_seeds"])
                    for disorder_seed in seed_values:
                        seed = int(disorder_seed) + 29 * graph_seed + int(round(1000 * float(disorder_strength)))
                        site_energies = static_disorder_energies(
                            n_sites,
                            float(disorder_strength) * float(config["coupling_hz"]),
                            seed=seed,
                        )
                        result = simulate_transport(
                            adjacency=instance.adjacency,
                            coupling_hz=float(config["coupling_hz"]),
                            dephasing_rate_hz=0.0,
                            sink_rate_hz=0.0,
                            loss_rate_hz=0.0,
                            times=times,
                            initial_site=initial_site,
                            trap_site=target_site,
                            site_energies_hz=site_energies,
                            node_coordinates=instance.coordinates,
                        )
                        msd = float(result.mean_squared_displacement_t[-1]) if result.mean_squared_displacement_t is not None else 0.0
                        front_width = float(result.front_width_t[-1]) if result.front_width_t is not None else 0.0
                        rows.append(
                            {
                                "paper_key": "anderson_1958",
                                "family": family,
                                "n_sites": n_sites,
                                "instance_id": instance.instance_id,
                                "graph_seed": graph_seed,
                                "disorder_seed": int(disorder_seed),
                                "disorder_strength_over_coupling": float(disorder_strength),
                                "participation_ratio": result.final_participation_ratio,
                                "ipr": result.final_ipr,
                                "msd": msd,
                                "front_width": front_width,
                                "entropy": result.final_entropy,
                                "arrival": float(result.node_populations[-1, target_site]),
                                "target_site": target_site,
                            }
                        )
                        validation["max_trace_deviation"] = max(validation["max_trace_deviation"], result.max_trace_deviation)
                        validation["max_population_closure_error"] = max(validation["max_population_closure_error"], result.max_population_closure_error)
                        validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], result.min_state_eigenvalue)
    return rows, validation


def _load_or_build_fractal_paper_benchmark(output_dir: Path) -> list[dict[str, object]]:
    summary_path = ROOT / "outputs" / "transport_networks" / "fractal_geometry_followup" / "latest" / "fractal_scaling_summary.csv"
    series_path = ROOT / "outputs" / "transport_networks" / "fractal_geometry_followup" / "latest" / "fractal_series.json"
    rows: list[dict[str, object]] = []
    source_rows = _read_csv_records(summary_path)
    if source_rows:
        lattice_by_n = {
            int(float(row.get("n_sites", 0) or 0)): row
            for row in source_rows
            if str(row.get("family", "")) == "square_lattice_2d"
        }
        for row in source_rows:
            if str(row.get("family", "")) == "square_lattice_2d":
                continue
            converted = dict(row)
            converted["paper_key"] = "rojo_francas_2024"
            converted["source_file"] = str(summary_path)
            n_sites = int(float(converted.get("n_sites", 0) or 0))
            control = lattice_by_n.get(n_sites)
            if control is not None:
                converted["control_family"] = "square_lattice_2d"
                converted["control_final_msd"] = control.get("final_msd", "")
                converted["control_final_front_width"] = control.get("final_front_width", "")
                converted["control_msd_exponent"] = control.get("msd_exponent", "")
                converted["msd_exponent_delta_abs"] = abs(float(converted.get("msd_exponent", 0.0) or 0.0) - float(control.get("msd_exponent", 0.0) or 0.0))
                converted["front_width_delta_abs"] = abs(float(converted.get("final_front_width", 0.0) or 0.0) - float(control.get("final_front_width", 0.0) or 0.0))
            else:
                converted["msd_exponent_delta_abs"] = ""
                converted["front_width_delta_abs"] = ""
            if "verdict" not in converted:
                changed = float(converted.get("msd_exponent_delta_abs", 0.0) or 0.0) >= 0.15 or float(converted.get("front_width_delta_abs", 0.0) or 0.0) >= 0.10
                converted["verdict"] = "fractal_geometry_changes_spreading" if changed else "inconclusive"
            rows.append(converted)
        return rows
    series = _read_json(series_path)
    if isinstance(series, dict):
        for key, payload in series.items():
            if not isinstance(payload, dict):
                continue
            exponent = estimate_msd_exponent(payload.get("times", []), payload.get("msd", []))
            rows.append(
                {
                    "paper_key": "rojo_francas_2024",
                    "family": str(payload.get("family", key)),
                    "msd_exponent": "" if exponent is None else exponent,
                    "verdict": "inconclusive",
                    "source_file": str(series_path),
                }
            )
    return rows


def _build_noisy_network_benchmark(
    stat_rows: list[dict[str, object]],
    dynamic_records: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_family_delta: dict[str, list[float]] = defaultdict(list)
    for record in dynamic_records:
        family = str(record.get("family", ""))
        if not family:
            continue
        by_family_delta[family].append(float(record.get("quantum_minus_classical_arrival", record.get("quantum_minus_classical", 0.0)) or 0.0))
    rows: list[dict[str, object]] = []
    for row in stat_rows:
        family = str(row.get("family", ""))
        if not family:
            continue
        deltas = by_family_delta.get(family, [])
        rows.append(
            {
                "paper_key": "walschaers_2016_coutinho_2022",
                "family": family,
                "edge_model": row.get("edge_model", ""),
                "target_style": row.get("target_style", ""),
                "disorder_strength_over_coupling": row.get("disorder_strength_over_coupling", ""),
                "best_dephasing_over_coupling": row.get("best_dephasing_over_coupling", ""),
                "dephasing_gain_mean": row.get("dephasing_gain_mean", ""),
                "dephasing_gain_ci95_low": row.get("dephasing_gain_ci95_low", ""),
                "arrival_mean": row.get("best_arrival_mean", ""),
                "arrival_std": row.get("best_arrival_std", row.get("best_arrival_sem", "")),
                "quantum_minus_classical_mean": float(np.mean(deltas)) if deltas else 0.0,
            }
        )
    return rows


def _run_steady_state_transport_benchmark(config: dict[str, object]) -> list[dict[str, object]]:
    aux = _auxiliary_profile_config(config)
    rows: list[dict[str, object]] = []
    for family in list(aux["steady_families"]):
        family = str(family)
        for n_sites in list(aux["n_sites_values"]):
            n_sites = int(n_sites)
            graph_seed = int(config["graph_seed_base"]) + 66_000 + n_sites + len(rows)
            instance = _instance_for_auxiliary(family, n_sites, graph_seed, 0)
            source_site = n_sites - 1
            drain_site = int(target_candidates(instance, initial_site=source_site).get("far", 0))
            for disorder_strength in [0.0, 1.0]:
                site_energies = static_disorder_energies(
                    n_sites,
                    float(disorder_strength) * float(config["coupling_hz"]),
                    seed=graph_seed + int(1000 * disorder_strength),
                )
                for gamma in [0.0, 0.2]:
                    result = solve_effective_source_drain_steady_state(
                        instance.adjacency,
                        source_site=source_site,
                        drain_site=drain_site,
                        coupling_hz=float(config["coupling_hz"]),
                        dephasing_rate_hz=float(gamma) * float(config["coupling_hz"]),
                        reset_rate_hz=float(config["sink_rate_hz"]),
                        site_energies_hz=site_energies,
                    )
                    rows.append(
                        {
                            "paper_key": "manzano_2013",
                            "family": family,
                            "n_sites": n_sites,
                            "instance_id": instance.instance_id,
                            "source_site": source_site,
                            "drain_site": drain_site,
                            "disorder_strength_over_coupling": disorder_strength,
                            "dephasing_over_coupling": gamma,
                            "current": result["current"],
                            "drain_population": result["drain_population"],
                            "trace_error": result["trace_error"],
                            "min_eigenvalue": result["min_eigenvalue"],
                            "residual_norm": result["residual_norm"],
                            "model_note": "trace-preserving source-drain reset NESS, separate from absorbing sink model",
                        }
                    )
    return rows


def _write_claim_table(claims: list[dict[str, object]], output_path: Path) -> None:
    fields = [
        "paper_key",
        "claim_id",
        "expected_trend",
        "observed_metric",
        "threshold",
        "observed_value",
        "verdict",
        "confidence",
        "reason",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for claim in claims:
            writer.writerow({field: claim.get(field, "") for field in fields})


def _plot_paper_verdict_overview(verdicts: dict[str, dict[str, object]], output_path: Path) -> None:
    paper_keys = sorted(verdicts)
    verdict_order = ["matched", "diverged", "inconclusive", "not_applicable"]
    fig_height = max(4.0, 0.38 * len(paper_keys) + 1.2)
    fig, ax = plt.subplots(figsize=(9.0, fig_height))
    left = [0] * len(paper_keys)
    for verdict in verdict_order:
        values = []
        for paper_key in paper_keys:
            counts = verdicts[paper_key].get("counts", {})
            values.append(int(counts.get(verdict, 0)) if isinstance(counts, dict) else 0)
        ax.barh(paper_keys, values, left=left, label=verdict, color=VERDICT_COLORS[verdict])
        left = [current + value for current, value in zip(left, values)]
    ax.set_xlabel("Number of evaluated claims")
    ax.set_title("Paper-by-paper reproduction verdicts")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_claim_confidence(claims: list[dict[str, object]], output_path: Path) -> None:
    labels = [f"{claim['paper_key']}\n{claim['claim_id']}" for claim in claims]
    confidences = [float(claim.get("confidence", 0.0)) for claim in claims]
    colors = [VERDICT_COLORS.get(str(claim.get("verdict")), "#455a64") for claim in claims]
    fig_height = max(4.0, 0.42 * len(claims) + 1.2)
    fig, ax = plt.subplots(figsize=(10.0, fig_height))
    ax.barh(labels, confidences, color=colors)
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("Traceable confidence score")
    ax.set_title("Claim-level confidence by paper")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _write_report(
    *,
    output_dir: Path,
    profile: str,
    metrics: dict[str, object],
    claims: list[dict[str, object]],
    verdicts: dict[str, dict[str, object]],
) -> None:
    verdict_counts = Counter(str(item.get("verdict", "")) for item in verdicts.values())
    lines = [
        "# Paper Reproduction And Validation Suite",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        f"Profile: `{profile}`",
        "",
        "## Scope",
        "",
        "This suite does not claim exact numerical reproduction of every paper. It tests whether the effective finite-network model reproduces the paper-level trend, control, or methodological claim that is relevant to this project.",
        "",
        "## Newly Implemented Paper Benchmarks",
        "",
        "- `coates_2023`: full arrival-versus-dephasing curves are exported in `gamma_resolved_curves.csv` and checked for separated local optima.",
        "- `rojo_francas_2024`: fractal spreading diagnostics are exported in `fractal_paper_benchmark.csv` and compared against a square-lattice control.",
        "- `anderson_1958`: static-disorder localization is tested in `localization_disorder_benchmark.csv` using participation ratio, IPR, MSD and target population.",
        "- `walschaers_2016`: noisy/disordered network ensemble statistics are summarized in `noisy_network_benchmark.csv` using mean, spread and gain.",
        "- `manzano_2013`: stationary transport is handled by a separate source-drain NESS benchmark in `steady_state_transport_benchmark.csv`, not by the absorbing sink model.",
        "- `coutinho_2022`: noisy quantum-network signatures are compared against classical/topological controls through the noisy-network benchmark table.",
        "",
        "## Overall Status",
        "",
        f"- Papers matched: {verdict_counts.get('matched', 0)}.",
        f"- Papers diverged: {verdict_counts.get('diverged', 0)}.",
        f"- Papers inconclusive: {verdict_counts.get('inconclusive', 0)}.",
        f"- Papers not applicable: {verdict_counts.get('not_applicable', 0)}.",
        f"- Numerical validation passed: {metrics.get('numerics_pass', False)}.",
        f"- Open dynamic signatures evaluated: {metrics.get('open_signature_count', 'unknown')}.",
        "",
        "## Paper-By-Paper Status",
        "",
        "| Paper | Verdict | Claims | Mean confidence | Short reading |",
        "|---|---:|---:|---:|---|",
    ]
    for paper_key, payload in sorted(verdicts.items()):
        paper_claims = [claim for claim in claims if claim.get("paper_key") == paper_key]
        central = [claim for claim in paper_claims if claim.get("verdict") != "not_applicable"]
        matched = sum(1 for claim in central if claim.get("verdict") == "matched")
        reading = f"{matched}/{len(central)} central claims matched" if central else "Outside model scope"
        lines.append(
            f"| `{paper_key}` | `{payload.get('verdict', 'unknown')}` | {payload.get('claim_count', 0)} | "
            f"{float(payload.get('mean_confidence', 0.0)):.2f} | {reading}. |"
        )
    lines.extend(
        [
            "",
            "## Claim Details",
            "",
            "| Paper | Claim | Expected trend | Observed metric | Threshold | Observed value | Verdict | Reason |",
            "|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    for claim in claims:
        lines.append(
            "| "
            f"`{claim.get('paper_key', '')}` | "
            f"`{claim.get('claim_id', '')}` | "
            f"{claim.get('expected_trend', '')} | "
            f"`{claim.get('observed_metric', '')}` | "
            f"`{claim.get('threshold', '')}` | "
            f"`{claim.get('observed_value', '')}` | "
            f"`{claim.get('verdict', '')}` | "
            f"{claim.get('reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "![Paper verdict overview](figures/paper_verdict_overview.png)",
            "",
            "![Claim confidence](figures/paper_claim_confidence.png)",
            "",
            "## Interpretation Rule",
            "",
            "- `matched`: the expected direction appears and passes the stated threshold.",
            "- `diverged`: the opposite direction appears with enough support.",
            "- `inconclusive`: the current profile is under-resolved or the effect is below threshold.",
            "- `not_applicable`: the current effective model lacks the required microscopic detail.",
            "",
            "## Next Action",
            "",
            "Run the `paper` profile if this was a smoke run. Run `confirm` only for claims that remain strong, divergent, or scientifically important but inconclusive.",
            "",
        ]
    )
    (output_dir / "paper_reproduction_report.md").write_text("\n".join(lines), encoding="utf-8")


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


def run_suite(config: dict[str, object], output_dir: Path, *, reuse_validation: bool = False) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    if reuse_validation and (output_dir / "metrics.json").exists():
        metrics = _read_json(output_dir / "metrics.json")
    else:
        metrics = run_validation(config, output_dir)
    benchmark_payload = _read_json(output_dir / "benchmark_records.json")
    stat_payload = _read_json(output_dir / "statistical_summary.json")
    group_report = _read_json(output_dir / "group_split_report.json")
    size_report = _read_json(output_dir / "size_generalization_report.json")
    records = _read_csv_records(output_dir / "dynamic_signatures_with_classical.csv")
    closed_records = benchmark_payload.get("closed_walk_records", [])
    target_records = benchmark_payload.get("target_position_records", [])
    stat_rows = stat_payload.get("rows", [])

    if not isinstance(closed_records, list):
        closed_records = []
    if not isinstance(target_records, list):
        target_records = []
    if not isinstance(stat_rows, list):
        stat_rows = []

    gamma_curve_records, gamma_validation = _run_gamma_resolved_curves(config)
    localization_records, localization_validation = _run_localization_disorder_benchmark(config)
    fractal_records = _load_or_build_fractal_paper_benchmark(output_dir)
    noisy_network_records = _build_noisy_network_benchmark(stat_rows, records)
    steady_state_records = _run_steady_state_transport_benchmark(config)

    _write_records_csv(gamma_curve_records, output_dir / "gamma_resolved_curves.csv")
    _write_records_csv(fractal_records, output_dir / "fractal_paper_benchmark.csv")
    _write_records_csv(localization_records, output_dir / "localization_disorder_benchmark.csv")
    _write_records_csv(steady_state_records, output_dir / "steady_state_transport_benchmark.csv")
    _write_records_csv(noisy_network_records, output_dir / "noisy_network_benchmark.csv")

    auxiliary_validation = {
        "gamma_resolved_curves": gamma_validation,
        "localization_disorder": localization_validation,
        "steady_state_records": len(steady_state_records),
    }

    claims = evaluate_paper_claims(
        closed_records=closed_records,
        target_records=target_records,
        records=records,
        stat_rows=stat_rows,
        group_report=group_report,
        size_report=size_report,
        metrics=metrics,
        gamma_curve_records=gamma_curve_records,
        fractal_records=fractal_records,
        localization_records=localization_records,
        steady_state_records=steady_state_records,
        noisy_network_records=noisy_network_records,
    )
    claim_payload = [paper_claim_to_dict(claim) for claim in claims]
    verdicts = aggregate_paper_verdicts(claims)

    (output_dir / "paper_claims.json").write_text(json.dumps(claim_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "paper_verdicts.json").write_text(json.dumps(verdicts, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_claim_table(claim_payload, output_dir / "paper_reproduction_table.csv")
    _plot_paper_verdict_overview(verdicts, figures_dir / "paper_verdict_overview.png")
    _plot_claim_confidence(claim_payload, figures_dir / "paper_claim_confidence.png")
    _write_report(output_dir=output_dir, profile=str(config["profile"]), metrics=metrics, claims=claim_payload, verdicts=verdicts)

    paper_metrics = {
        **metrics,
        "paper_suite_profile": config["profile"],
        "paper_claim_count": len(claim_payload),
        "paper_verdict_counts": dict(Counter(str(item.get("verdict", "")) for item in verdicts.values())),
        "gamma_resolved_curve_record_count": len(gamma_curve_records),
        "fractal_paper_benchmark_record_count": len(fractal_records),
        "localization_disorder_record_count": len(localization_records),
        "steady_state_transport_record_count": len(steady_state_records),
        "noisy_network_benchmark_record_count": len(noisy_network_records),
        "auxiliary_validation": auxiliary_validation,
    }
    (output_dir / "paper_suite_metrics.json").write_text(json.dumps(paper_metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return paper_metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run paper-by-paper reproduction benchmarks for open-transport network dynamics.")
    parser.add_argument("--profile", choices=["smoke", "paper", "confirm"], default="smoke")
    parser.add_argument("--output-subdir", default="paper_reproduction_suite")
    parser.add_argument("--reuse-existing-validation", action="store_true", help="Skip simulation if the validation artifacts already exist in the output directory.")
    args = parser.parse_args(argv)
    config = profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_suite(config, output_dir, reuse_validation=args.reuse_existing_validation)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
