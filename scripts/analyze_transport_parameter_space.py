from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
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

from oqs_transport import generate_network_instance, target_candidates  # noqa: E402
from scripts.run_transport_dynamic_network_atlas import (  # noqa: E402
    RANDOM_FAMILIES as ATLAS_RANDOM_FAMILIES,
    _graph_seed as _atlas_graph_seed,
    _realization_count as _atlas_realization_count,
    _unique_targets as _atlas_unique_targets,
    profile_config as atlas_profile_config,
)
from scripts.run_transport_paper_reproduction_suite import (  # noqa: E402
    _auxiliary_profile_config as paper_auxiliary_profile_config,
    profile_config as paper_profile_config,
)


OUTPUT_DIR = ROOT / "outputs" / "transport_networks" / "parameter_space_analysis" / "latest"

VALIDATION_RANDOM_FAMILIES = {
    "erdos_renyi",
    "watts_strogatz_small_world",
    "barabasi_albert_scale_free",
    "modular_two_community",
    "random_geometric",
}

FAMILY_CLASS = {
    "chain": "deterministic_sparse",
    "ring": "deterministic_sparse",
    "complete": "deterministic_dense",
    "star": "deterministic_hub",
    "erdos_renyi": "random_graph",
    "watts_strogatz_small_world": "random_graph",
    "barabasi_albert_scale_free": "random_graph",
    "modular_two_community": "random_graph",
    "random_geometric": "random_spatial",
    "square_lattice_2d": "deterministic_spatial",
    "bottleneck": "deterministic_spatial",
    "clustered": "deterministic_spatial",
    "sierpinski_gasket": "deterministic_fractal",
    "sierpinski_carpet_like": "deterministic_fractal",
}


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _graph_stats(family: str, n_sites: int, seed: int, realization: int) -> dict[str, float]:
    instance = generate_network_instance(family, n_sites=n_sites, seed=seed, realization_index=realization)
    adjacency = np.asarray(instance.adjacency, dtype=float)
    edge_count = int(np.count_nonzero(np.triu(adjacency, k=1)))
    possible = max(n_sites * (n_sites - 1) / 2, 1.0)
    degrees = np.sum(adjacency > 0.0, axis=1)
    initial_site = n_sites - 1
    raw_targets = target_candidates(instance, initial_site=initial_site)
    unique_target_count = len(set(int(site) for site in raw_targets.values()))
    duplicate_target_styles = len(raw_targets) - unique_target_count
    return {
        "edge_count": float(edge_count),
        "density": float(edge_count / possible),
        "mean_degree": float(np.mean(degrees)),
        "max_degree": float(np.max(degrees)),
        "unique_candidate_targets": float(unique_target_count),
        "duplicate_target_styles": float(duplicate_target_styles),
    }


def _append_atlas_profile_rows(profile: str, rows: list[dict[str, object]]) -> dict[str, object]:
    config = atlas_profile_config(profile)
    gamma_count = len(config["dephasing_over_coupling"])
    disorder_count = len(config["disorder_strength_over_coupling"])
    disorder_seed_count = len(config["disorder_seeds"])
    n_time_samples = int(config["n_time_samples"])
    total = defaultdict(float)
    for family in list(config["families"]):
        family = str(family)
        for n_sites in list(config["n_sites_values"]):
            n_sites = int(n_sites)
            realization_count = _atlas_realization_count(family, config)
            for realization in range(realization_count):
                seed = _atlas_graph_seed(config, family=family, n_sites=n_sites, realization=realization)
                instance = generate_network_instance(family, n_sites=n_sites, seed=seed, realization_index=realization)
                initial_site = n_sites - 1
                targets = _atlas_unique_targets(instance, initial_site=initial_site, target_styles=list(config["target_styles"]))
                target_count = len(targets)
                record_count = target_count * disorder_count * disorder_seed_count
                quantum_simulations = record_count * gamma_count
                classical_simulations = record_count
                graph = _graph_stats(family, n_sites, seed, realization)
                dim = n_sites + 2
                cost_units = quantum_simulations * n_time_samples * (dim**4) * max(graph["density"], 1.0 / max(n_sites, 1))
                row = {
                    "campaign": "dynamic_network_atlas",
                    "profile": profile,
                    "family": family,
                    "family_class": FAMILY_CLASS.get(family, "unknown"),
                    "n_sites": n_sites,
                    "realization": realization,
                    "target_styles_requested": len(config["target_styles"]),
                    "unique_targets_used": target_count,
                    "disorder_values": disorder_count,
                    "disorder_seeds": disorder_seed_count,
                    "gamma_values": gamma_count,
                    "time_samples": n_time_samples,
                    "records": record_count,
                    "quantum_simulations": quantum_simulations,
                    "classical_simulations": classical_simulations,
                    "estimated_cost_units": float(cost_units),
                    **graph,
                }
                rows.append(row)
                for key in ("records", "quantum_simulations", "classical_simulations", "estimated_cost_units"):
                    total[key] += float(row[key])
                total["graph_instances"] += 1
    total.update({"campaign": "dynamic_network_atlas", "profile": profile})
    return dict(total)


def _validation_edge_model_count(config: dict[str, object], family: str) -> int:
    edge_models = set(config.get("edge_models_main", ["unweighted"]))
    sensitivity_families = set(config.get("edge_sensitivity_families", config["families"]))
    if family in sensitivity_families:
        edge_models |= set(config.get("edge_models_sensitivity", []))
    return len(edge_models)


def _append_paper_validation_rows(profile: str, rows: list[dict[str, object]]) -> dict[str, object]:
    config = paper_profile_config(profile)
    gamma_count = len(config["dephasing_over_coupling"])
    disorder_count = len(config["disorder_strength_over_coupling"])
    disorder_seed_count = len(config["disorder_seeds"])
    target_style_count = len(config["target_styles"])
    n_time_samples = int(config["n_time_samples"])
    total = defaultdict(float)
    for family in list(config["families"]):
        family = str(family)
        realization_count = int(config["graph_realizations"]) if family in VALIDATION_RANDOM_FAMILIES else int(config["deterministic_graph_realizations"])
        edge_model_count = _validation_edge_model_count(config, family)
        for n_sites in list(config["n_sites_values"]):
            n_sites = int(n_sites)
            for realization in range(realization_count):
                seed = int(config["graph_seed_base"]) + 10_000 * n_sites + 101 * realization
                if family not in VALIDATION_RANDOM_FAMILIES:
                    seed = int(config["graph_seed_base"]) + n_sites + realization
                graph = _graph_stats(family, n_sites, seed, realization)
                record_count = edge_model_count * target_style_count * disorder_count * disorder_seed_count
                quantum_simulations = record_count * gamma_count
                classical_simulations = record_count
                dim = n_sites + 2
                cost_units = quantum_simulations * n_time_samples * (dim**4) * max(graph["density"], 1.0 / max(n_sites, 1))
                row = {
                    "campaign": "paper_reproduction_suite_validation",
                    "profile": profile,
                    "family": family,
                    "family_class": FAMILY_CLASS.get(family, "unknown"),
                    "n_sites": n_sites,
                    "realization": realization,
                    "edge_models": edge_model_count,
                    "target_styles_requested": target_style_count,
                    "unique_targets_used": graph["unique_candidate_targets"],
                    "disorder_values": disorder_count,
                    "disorder_seeds": disorder_seed_count,
                    "gamma_values": gamma_count,
                    "time_samples": n_time_samples,
                    "records": record_count,
                    "quantum_simulations": quantum_simulations,
                    "classical_simulations": classical_simulations,
                    "estimated_cost_units": float(cost_units),
                    **graph,
                }
                rows.append(row)
                for key in ("records", "quantum_simulations", "classical_simulations", "estimated_cost_units"):
                    total[key] += float(row[key])
                total["graph_instances"] += 1
    total.update({"campaign": "paper_reproduction_suite_validation", "profile": profile})
    return dict(total)


def _append_paper_auxiliary_rows(profile: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    config = paper_profile_config(profile)
    aux = paper_auxiliary_profile_config(config)
    n_values = list(aux["n_sites_values"])
    disorder_seeds = list(aux["disorder_seeds"])

    coates_rows = len(aux["coates_families"]) * len(n_values) * len(aux["coates_disorder"]) * len(disorder_seeds) * len(aux["coates_gamma"])
    rows.append(
        {
            "campaign": "paper_reproduction_suite_auxiliary",
            "profile": profile,
            "block": "coates_gamma_resolved_curves",
            "families": len(aux["coates_families"]),
            "n_values": len(n_values),
            "disorder_values": len(aux["coates_disorder"]),
            "disorder_seeds": len(disorder_seeds),
            "gamma_values": len(aux["coates_gamma"]),
            "quantum_simulations": coates_rows,
            "records": coates_rows,
            "classical_simulations": 0,
            "note": "Each row is one gamma-resolved quantum simulation.",
        }
    )

    anderson_rows = len(aux["anderson_families"]) * len(n_values) * len(aux["anderson_disorder"]) * len(disorder_seeds)
    rows.append(
        {
            "campaign": "paper_reproduction_suite_auxiliary",
            "profile": profile,
            "block": "anderson_disorder_localization",
            "families": len(aux["anderson_families"]),
            "n_values": len(n_values),
            "disorder_values": len(aux["anderson_disorder"]),
            "disorder_seeds": len(disorder_seeds),
            "gamma_values": 1,
            "quantum_simulations": anderson_rows,
            "records": anderson_rows,
            "classical_simulations": 0,
            "note": "Closed coherent simulations at different static disorder strengths.",
        }
    )

    steady_rows = len(aux["steady_families"]) * len(n_values) * 2 * 2
    rows.append(
        {
            "campaign": "paper_reproduction_suite_auxiliary",
            "profile": profile,
            "block": "manzano_steady_state_source_drain",
            "families": len(aux["steady_families"]),
            "n_values": len(n_values),
            "disorder_values": 2,
            "disorder_seeds": 1,
            "gamma_values": 2,
            "quantum_simulations": 0,
            "steady_state_solves": steady_rows,
            "records": steady_rows,
            "classical_simulations": 0,
            "note": "Linear NESS solves, separate from finite-time absorbing sink simulations.",
        }
    )
    return rows


def _summary_rows(rows: list[dict[str, object]], auxiliary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["campaign"]), str(row["profile"]))].append(row)
    summary: list[dict[str, object]] = []
    for (campaign, profile), items in sorted(grouped.items()):
        summary.append(
            {
                "campaign": campaign,
                "profile": profile,
                "graph_instances": len(items),
                "records": int(sum(float(row.get("records", 0.0)) for row in items)),
                "quantum_simulations": int(sum(float(row.get("quantum_simulations", 0.0)) for row in items)),
                "classical_simulations": int(sum(float(row.get("classical_simulations", 0.0)) for row in items)),
                "estimated_cost_units": float(sum(float(row.get("estimated_cost_units", 0.0)) for row in items)),
                "max_family_record_share": _max_family_share(items),
            }
        )
    for row in auxiliary_rows:
        summary.append(row)
    return summary


def _max_family_share(items: list[dict[str, object]]) -> float:
    by_family = defaultdict(float)
    total = 0.0
    for row in items:
        value = float(row.get("records", 0.0))
        by_family[str(row.get("family", ""))] += value
        total += value
    return float(max(by_family.values(), default=0.0) / max(total, 1.0))


def _factor_rows() -> list[dict[str, object]]:
    atlas_strong = atlas_profile_config("strong")
    atlas_intense = atlas_profile_config("intense")
    atlas_prep = atlas_profile_config("evidence_prep")
    paper = paper_profile_config("paper")
    return [
        {
            "profile": "atlas_strong",
            "families": len(atlas_strong["families"]),
            "n_values": len(atlas_strong["n_sites_values"]),
            "random_realizations": atlas_strong["graph_realizations"],
            "deterministic_realizations": atlas_strong["deterministic_graph_realizations"],
            "target_styles": len(atlas_strong["target_styles"]),
            "disorder_values": len(atlas_strong["disorder_strength_over_coupling"]),
            "disorder_seeds": len(atlas_strong["disorder_seeds"]),
            "gamma_values": len(atlas_strong["dephasing_over_coupling"]),
            "time_samples": atlas_strong["n_time_samples"],
        },
        {
            "profile": "atlas_intense",
            "families": len(atlas_intense["families"]),
            "n_values": len(atlas_intense["n_sites_values"]),
            "random_realizations": atlas_intense["graph_realizations"],
            "deterministic_realizations": atlas_intense["deterministic_graph_realizations"],
            "target_styles": len(atlas_intense["target_styles"]),
            "disorder_values": len(atlas_intense["disorder_strength_over_coupling"]),
            "disorder_seeds": len(atlas_intense["disorder_seeds"]),
            "gamma_values": len(atlas_intense["dephasing_over_coupling"]),
            "time_samples": atlas_intense["n_time_samples"],
        },
        {
            "profile": "atlas_evidence_prep",
            "families": len(atlas_prep["families"]),
            "n_values": len(atlas_prep["n_sites_values"]),
            "random_realizations": atlas_prep["graph_realizations"],
            "deterministic_realizations": atlas_prep["deterministic_graph_realizations"],
            "target_styles": len(atlas_prep["target_styles"]),
            "disorder_values": len(atlas_prep["disorder_strength_over_coupling"]),
            "disorder_seeds": len(atlas_prep["disorder_seeds"]),
            "gamma_values": len(atlas_prep["dephasing_over_coupling"]),
            "time_samples": atlas_prep["n_time_samples"],
        },
        {
            "profile": "paper_validation",
            "families": len(paper["families"]),
            "n_values": len(paper["n_sites_values"]),
            "random_realizations": paper["graph_realizations"],
            "deterministic_realizations": paper["deterministic_graph_realizations"],
            "target_styles": len(paper["target_styles"]),
            "disorder_values": len(paper["disorder_strength_over_coupling"]),
            "disorder_seeds": len(paper["disorder_seeds"]),
            "gamma_values": len(paper["dephasing_over_coupling"]),
            "time_samples": paper["n_time_samples"],
        },
    ]


def _plot_dashboard(summary: list[dict[str, object]], rows: list[dict[str, object]], output_path: Path) -> None:
    main = [row for row in summary if "block" not in row]
    labels = [f"{row['campaign']}\n{row['profile']}" for row in main]
    quantum = [float(row.get("quantum_simulations", 0.0)) for row in main]
    classical = [float(row.get("classical_simulations", 0.0)) for row in main]

    by_family = defaultdict(float)
    for row in rows:
        if row.get("profile") != "strong":
            continue
        by_family[str(row.get("family"))] += float(row.get("quantum_simulations", 0.0))
    families = sorted(by_family, key=by_family.get, reverse=True)
    family_values = [by_family[family] for family in families]

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.5), constrained_layout=True)
    x = np.arange(len(labels))
    axes[0].bar(x - 0.18, quantum, width=0.36, label="quantum simulations", color="#2563eb")
    axes[0].bar(x + 0.18, classical, width=0.36, label="classical controls", color="#f97316")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=18, ha="right")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("count, log scale")
    axes[0].set_title("Where the parameter grid explodes")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].barh(families, family_values, color="#0f766e")
    axes[1].invert_yaxis()
    axes[1].set_xscale("log")
    axes[1].set_xlabel("quantum simulations in atlas strong, log scale")
    axes[1].set_title("Family contribution in the strong atlas")
    axes[1].grid(axis="x", alpha=0.25)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_report(summary: list[dict[str, object]], rows: list[dict[str, object]], output_path: Path) -> None:
    summary_by_key = {(str(row.get("campaign")), str(row.get("profile"))): row for row in summary if "block" not in row}
    atlas_strong = summary_by_key.get(("dynamic_network_atlas", "strong"), {})
    atlas_intense = summary_by_key.get(("dynamic_network_atlas", "intense"), {})
    atlas_prep = summary_by_key.get(("dynamic_network_atlas", "evidence_prep"), {})
    paper = summary_by_key.get(("paper_reproduction_suite_validation", "paper"), {})
    strong_rows = [row for row in rows if row.get("campaign") == "dynamic_network_atlas" and row.get("profile") == "strong"]
    family_records = defaultdict(float)
    family_cost = defaultdict(float)
    for row in strong_rows:
        family_records[str(row["family"])] += float(row["records"])
        family_cost[str(row["family"])] += float(row["estimated_cost_units"])
    top_records = sorted(family_records.items(), key=lambda item: item[1], reverse=True)[:5]
    top_cost = sorted(family_cost.items(), key=lambda item: item[1], reverse=True)[:5]
    lines = [
        "# Parameter-Space And Combinatorial Explosion Analysis",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        "",
        "## What Explodes",
        "",
        "The dominant multiplier is not one variable alone. It is:",
        "",
        "`families x N values x graph realizations x target choices x disorder values x disorder seeds x dephasing values`.",
        "",
        "For each final record, the quantum model runs a full dephasing scan. Therefore, adding one extra value of `gamma/J` multiplies every graph/target/disorder case.",
        "",
        "## Main Counts",
        "",
        "| Campaign/profile | Records | Quantum simulations | Classical controls | Graph instances |",
        "|---|---:|---:|---:|---:|",
        f"| Atlas evidence prep | {int(atlas_prep.get('records', 0))} | {int(atlas_prep.get('quantum_simulations', 0))} | {int(atlas_prep.get('classical_simulations', 0))} | {int(atlas_prep.get('graph_instances', 0))} |",
        f"| Atlas strong | {int(atlas_strong.get('records', 0))} | {int(atlas_strong.get('quantum_simulations', 0))} | {int(atlas_strong.get('classical_simulations', 0))} | {int(atlas_strong.get('graph_instances', 0))} |",
        f"| Atlas intense | {int(atlas_intense.get('records', 0))} | {int(atlas_intense.get('quantum_simulations', 0))} | {int(atlas_intense.get('classical_simulations', 0))} | {int(atlas_intense.get('graph_instances', 0))} |",
        f"| Paper validation profile | {int(paper.get('records', 0))} | {int(paper.get('quantum_simulations', 0))} | {int(paper.get('classical_simulations', 0))} | {int(paper.get('graph_instances', 0))} |",
        "",
        "## Strong Atlas: Families That Dominate Record Count",
        "",
    ]
    for family, value in top_records:
        lines.append(f"- `{family}`: {int(value)} final records before multiplying interpretation/reporting.")
    lines.extend(["", "## Strong Atlas: Families That Dominate Estimated Compute Cost", ""])
    for family, value in top_cost:
        lines.append(f"- `{family}`: relative cost units `{value:.3e}`.")
    lines.extend(
        [
            "",
            "## Practical Reading",
            "",
            "- Random families are expensive because each size has many independent graph realizations.",
            "- Gamma/dephasing grids are expensive because every point requires a full Lindblad time evolution.",
            "- Disorder seeds are expensive but scientifically important because they give uncertainty and prevent one lucky disorder draw from becoming a claim.",
            "- Complete graphs are dense, so each simulation is structurally heavier, but they do not dominate total count because they have only one deterministic instance per size.",
            "- Fractals are not the biggest combinatorial load yet; they become expensive if we add many sizes and seeds.",
            "",
            "## Where To Cut First If The PC Is Busy",
            "",
            "1. Keep all families, but reduce random graph realizations before reducing physics grids.",
            "2. Keep `gamma/J = 0` and the suspected optimum window, but remove redundant high-gamma points unless testing the ceiling.",
            "3. Keep disorder seeds for candidate claims; reduce seeds only for exploratory scans.",
            "4. Do not run all target styles everywhere. Use `near/far` for atlas, then controlled target sweeps only where target position matters.",
            "5. Move strong atlas and confirm profiles to the Mac; keep evidence-prep and paper-specific refinements on this PC.",
            "",
            "## Outputs",
            "",
            "- `parameter_cost_summary.csv`: campaign-level counts.",
            "- `family_cost_breakdown.csv`: family/size/realization-level counts and graph density.",
            "- `combinatorial_factors.csv`: raw multipliers for each profile.",
            "- `auxiliary_benchmark_costs.csv`: Coates, Anderson and Manzano auxiliary benchmark counts.",
            "- `combinatorial_explosion_dashboard.png`: visual summary.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_analysis(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    auxiliary_rows: list[dict[str, object]] = []

    totals = [
        _append_atlas_profile_rows("evidence_prep", rows),
        _append_atlas_profile_rows("strong", rows),
        _append_atlas_profile_rows("intense", rows),
        _append_paper_validation_rows("paper", rows),
    ]
    for profile in ("paper", "confirm"):
        _append_paper_auxiliary_rows(profile, auxiliary_rows)

    summary = _summary_rows(rows, auxiliary_rows)
    _write_csv(summary, output_dir / "parameter_cost_summary.csv")
    _write_csv(rows, output_dir / "family_cost_breakdown.csv")
    _write_csv(_factor_rows(), output_dir / "combinatorial_factors.csv")
    _write_csv(auxiliary_rows, output_dir / "auxiliary_benchmark_costs.csv")
    _plot_dashboard(summary, rows, output_dir / "figures" / "combinatorial_explosion_dashboard.png")
    _write_report(summary, rows, output_dir / "parameter_space_report.md")
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "summary": summary,
        "profile_totals": totals,
        "output_dir": str(output_dir),
    }
    (output_dir / "parameter_space_metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> int:
    payload = run_analysis()
    print(json.dumps({"output_dir": payload["output_dir"], "summary_rows": len(payload["summary"])}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
