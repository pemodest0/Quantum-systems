from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
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

from oqs_transport import (  # noqa: E402
    adjacency_for_topology,
    classify_transport_regime,
    save_graph_topology_figure,
    save_population_animation_gif,
    simulate_transport,
    slugify,
    static_disorder_energies,
)


@dataclass(frozen=True)
class CollectionCase:
    name: str
    group: str
    topology: str
    n_sites: int
    coupling_hz: float
    sink_rate_hz: float
    loss_rate_hz: float
    initial_site: int
    trap_site: int
    disorder_strength_hz: float
    seeds: tuple[int, ...]


def _load_config(path: Path) -> tuple[dict[str, object], np.ndarray, np.ndarray, int, int, list[CollectionCase]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    times = np.linspace(float(raw["time_grid"]["t_final"]), float(raw["time_grid"]["t_final"]), 2)
    times = np.linspace(0.0, float(raw["time_grid"]["t_final"]), int(raw["time_grid"]["n_samples"]))
    dephasing_rates = np.asarray(raw["dephasing_rates_hz"], dtype=float)
    visualization = raw.get("visualization", {})
    animation_stride = int(visualization.get("animation_stride", 15))
    animation_fps = int(visualization.get("animation_fps", 12))
    cases = [
        CollectionCase(
            name=str(block["name"]),
            group=str(block["group"]),
            topology=str(block["topology"]),
            n_sites=int(block["n_sites"]),
            coupling_hz=float(block["coupling_hz"]),
            sink_rate_hz=float(block["sink_rate_hz"]),
            loss_rate_hz=float(block["loss_rate_hz"]),
            initial_site=int(block["initial_site"]),
            trap_site=int(block["trap_site"]),
            disorder_strength_hz=float(block["disorder_strength_hz"]),
            seeds=tuple(int(seed) for seed in block["seeds"]),
        )
        for block in raw["cases"]
    ]
    return raw, times, dephasing_rates, animation_stride, animation_fps, cases


def _stack_mean_std(arrays: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    stacked = np.stack(arrays, axis=0)
    if stacked.shape[0] == 1:
        return stacked[0], np.zeros_like(stacked[0])
    return np.mean(stacked, axis=0), np.std(stacked, axis=0, ddof=1)


def _run_case(case: CollectionCase, times: np.ndarray, dephasing_rates: np.ndarray) -> dict[str, object]:
    adjacency = adjacency_for_topology(case.topology, case.n_sites)
    rate_runs: list[dict[str, object]] = []
    representative_energies = None

    for rate in dephasing_rates:
        runs = []
        for seed in case.seeds:
            site_energies = (
                np.zeros(case.n_sites, dtype=float)
                if case.disorder_strength_hz == 0.0
                else static_disorder_energies(case.n_sites, case.disorder_strength_hz, seed)
            )
            if representative_energies is None:
                representative_energies = site_energies.copy()
            sim = simulate_transport(
                adjacency=adjacency,
                coupling_hz=case.coupling_hz,
                dephasing_rate_hz=float(rate),
                sink_rate_hz=case.sink_rate_hz,
                loss_rate_hz=case.loss_rate_hz,
                times=times,
                initial_site=case.initial_site,
                trap_site=case.trap_site,
                site_energies_hz=site_energies,
            )
            runs.append({"seed": seed, "site_energies_hz": site_energies, "simulation": sim})

        eff = np.array([run["simulation"].transport_efficiency for run in runs], dtype=float)
        coh = np.array([run["simulation"].mean_coherence_l1 for run in runs], dtype=float)
        loss = np.array([run["simulation"].loss_population[-1] for run in runs], dtype=float)
        trace_dev = np.array([run["simulation"].max_trace_deviation for run in runs], dtype=float)
        closure = np.array([run["simulation"].max_population_closure_error for run in runs], dtype=float)
        min_eig = np.array([run["simulation"].min_state_eigenvalue for run in runs], dtype=float)

        rate_runs.append(
            {
                "rate_hz": float(rate),
                "runs": runs,
                "efficiency_mean": float(np.mean(eff)),
                "efficiency_std": float(np.std(eff, ddof=1)) if eff.size > 1 else 0.0,
                "coherence_mean": float(np.mean(coh)),
                "coherence_std": float(np.std(coh, ddof=1)) if coh.size > 1 else 0.0,
                "loss_mean": float(np.mean(loss)),
                "loss_std": float(np.std(loss, ddof=1)) if loss.size > 1 else 0.0,
                "max_trace_deviation": float(np.max(trace_dev)),
                "max_population_closure_error": float(np.max(closure)),
                "min_state_eigenvalue": float(np.min(min_eig)),
            }
        )

    efficiency_curve = np.array([entry["efficiency_mean"] for entry in rate_runs], dtype=float)
    best_idx = int(np.argmax(efficiency_curve))
    best_rate_entry = rate_runs[best_idx]
    best_regime = classify_transport_regime(best_idx, len(dephasing_rates))

    population_mean, population_std = _stack_mean_std(
        [run["simulation"].node_populations for run in best_rate_entry["runs"]]
    )
    sink_mean, sink_std = _stack_mean_std([run["simulation"].sink_population for run in best_rate_entry["runs"]])
    loss_mean, loss_std = _stack_mean_std([run["simulation"].loss_population for run in best_rate_entry["runs"]])
    purity_mean, purity_std = _stack_mean_std([run["simulation"].purity_t for run in best_rate_entry["runs"]])
    entropy_mean, entropy_std = _stack_mean_std([run["simulation"].entropy_t for run in best_rate_entry["runs"]])
    pop_entropy_mean, pop_entropy_std = _stack_mean_std(
        [run["simulation"].population_shannon_entropy_t for run in best_rate_entry["runs"]]
    )
    pr_mean, pr_std = _stack_mean_std([run["simulation"].participation_ratio_t for run in best_rate_entry["runs"]])
    ipr_mean, ipr_std = _stack_mean_std([run["simulation"].ipr_t for run in best_rate_entry["runs"]])

    representative_run = max(best_rate_entry["runs"], key=lambda item: item["simulation"].transport_efficiency)
    return {
        "case": case,
        "adjacency": adjacency,
        "representative_site_energies_hz": representative_energies if representative_energies is not None else np.zeros(case.n_sites, dtype=float),
        "rate_runs": rate_runs,
        "efficiency_mean": np.array([entry["efficiency_mean"] for entry in rate_runs], dtype=float),
        "efficiency_std": np.array([entry["efficiency_std"] for entry in rate_runs], dtype=float),
        "coherence_mean": np.array([entry["coherence_mean"] for entry in rate_runs], dtype=float),
        "coherence_std": np.array([entry["coherence_std"] for entry in rate_runs], dtype=float),
        "loss_mean": np.array([entry["loss_mean"] for entry in rate_runs], dtype=float),
        "loss_std": np.array([entry["loss_std"] for entry in rate_runs], dtype=float),
        "best_idx": best_idx,
        "best_rate_hz": float(dephasing_rates[best_idx]),
        "best_regime": best_regime,
        "population_mean": population_mean,
        "population_std": population_std,
        "sink_mean": sink_mean,
        "sink_std": sink_std,
        "loss_mean_series": loss_mean,
        "loss_std_series": loss_std,
        "purity_mean_t": purity_mean,
        "purity_std_t": purity_std,
        "entropy_mean_t": entropy_mean,
        "entropy_std_t": entropy_std,
        "population_entropy_mean_t": pop_entropy_mean,
        "population_entropy_std_t": pop_entropy_std,
        "participation_ratio_mean_t": pr_mean,
        "participation_ratio_std_t": pr_std,
        "ipr_mean_t": ipr_mean,
        "ipr_std_t": ipr_std,
        "best_loss_mean": float(loss_mean[-1]),
        "best_loss_std": float(loss_std[-1]),
        "final_purity_mean": float(purity_mean[-1]),
        "final_purity_std": float(purity_std[-1]),
        "final_entropy_mean": float(entropy_mean[-1]),
        "final_entropy_std": float(entropy_std[-1]),
        "final_population_entropy_mean": float(pop_entropy_mean[-1]),
        "final_population_entropy_std": float(pop_entropy_std[-1]),
        "final_participation_ratio_mean": float(pr_mean[-1]),
        "final_participation_ratio_std": float(pr_std[-1]),
        "final_ipr_mean": float(ipr_mean[-1]),
        "final_ipr_std": float(ipr_std[-1]),
        "representative_run": representative_run,
        "best_rate_diagnostics": {
            "max_trace_deviation": float(best_rate_entry["max_trace_deviation"]),
            "max_population_closure_error": float(best_rate_entry["max_population_closure_error"]),
            "min_state_eigenvalue": float(best_rate_entry["min_state_eigenvalue"]),
        },
    }


def _plot_group_curves(path: Path, group_name: str, quantity_name: str, ylabel: str, dephasing_rates: np.ndarray, cases: list[dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    for case_result in cases:
        name = case_result["case"].name
        mean = case_result[f"{quantity_name}_mean"]
        std = case_result[f"{quantity_name}_std"]
        ax.plot(dephasing_rates, mean, marker="o", lw=1.8, label=name)
        if np.any(std > 0.0):
            ax.fill_between(dephasing_rates, mean - std, mean + std, alpha=0.18)
    ax.set_title(f"{group_name.capitalize()} cases: {ylabel}")
    ax.set_xlabel(r"Dephasing rate $\gamma_\phi$")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    ax.text(
        0.02,
        0.98,
        "Solid line = ensemble mean\nShaded band = sample standard deviation across seeds\nNo band = deterministic clean case",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.8,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.92},
    )
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_population_group(path: Path, group_name: str, cases: list[dict[str, object]], times: np.ndarray) -> None:
    fig, axes = plt.subplots(1, len(cases), figsize=(5.2 * len(cases), 4.8), sharey=True)
    if len(cases) == 1:
        axes = np.array([axes])

    for ax, case_result in zip(axes, cases, strict=True):
        case = case_result["case"]
        for site in range(case.n_sites):
            mean = case_result["population_mean"][:, site]
            std = case_result["population_std"][:, site]
            ax.plot(times, mean, lw=1.3, label=fr"$P_{{{site}}}(t)$")
            if np.any(std > 0.0):
                ax.fill_between(times, mean - std, mean + std, alpha=0.12)
        sink_mean = case_result["sink_mean"]
        sink_std = case_result["sink_std"]
        ax.plot(times, sink_mean, lw=2.0, ls="--", color="black", label=r"$P_{\mathrm{sink}}(t)$")
        if np.any(sink_std > 0.0):
            ax.fill_between(times, sink_mean - sink_std, sink_mean + sink_std, color="black", alpha=0.10)
        ax.set_title(f"{case.name}\n(best regime: {case_result['best_regime']})")
        ax.set_xlabel("Time")
        ax.grid(alpha=0.2)

    axes[0].set_ylabel("Population")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"{group_name.capitalize()} cases: population transport at the best dephasing rate", y=1.03)
    fig.text(
        0.5,
        -0.02,
        "Node populations are diagonal density-matrix elements. Dashed black curve is the sink population. Bands indicate ensemble spread when disorder is present.",
        ha="center",
        va="top",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_statmech_group(path: Path, group_name: str, cases: list[dict[str, object]], times: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.6), sharex=True)
    panels = [
        ("purity_mean_t", "purity_std_t", "Conditional network purity Tr(rho_net^2)"),
        ("entropy_mean_t", "entropy_std_t", "Conditional von Neumann entropy S(rho_net)"),
        ("population_entropy_mean_t", "population_entropy_std_t", "Shannon entropy of normalized node populations"),
        ("participation_ratio_mean_t", "participation_ratio_std_t", "Participation ratio of normalized node populations"),
    ]
    for ax, (mean_key, std_key, title) in zip(axes.ravel(), panels, strict=True):
        for case_result in cases:
            mean = case_result[mean_key]
            std = case_result[std_key]
            ax.plot(times, mean, lw=1.7, label=case_result["case"].name)
            if np.any(std > 0.0):
                ax.fill_between(times, mean - std, mean + std, alpha=0.14)
        ax.set_title(title)
        ax.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[1, 0].set_xlabel("Time")
    axes[1, 1].set_xlabel("Time")
    fig.suptitle(
        f"{group_name.capitalize()} cases: conditional statistical-mechanics observables at the best dephasing rate",
        y=1.02,
    )
    fig.text(
        0.5,
        -0.01,
        "These observables are evaluated on the normalized state restricted to the physical graph nodes, so sink capture does not artificially masquerade as internal mixing.",
        ha="center",
        va="top",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_pairwise_heatmap(path: Path, title: str, cases: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    labels = [case_result["case"].name for case_result in cases]
    values = np.array([case_result["efficiency_mean"][case_result["best_idx"]] for case_result in cases], dtype=float)
    matrix = values[:, None] - values[None, :]
    fig, ax = plt.subplots(figsize=(4.8 + 0.4 * len(labels), 4.2 + 0.2 * len(labels)))
    image = ax.imshow(matrix, cmap="coolwarm", vmin=-np.max(np.abs(matrix)), vmax=np.max(np.abs(matrix)))
    ax.set_xticks(np.arange(len(labels)), labels=labels, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(labels)), labels=labels)
    ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{matrix[i, j]:+.3f}", ha="center", va="center", fontsize=8, color="black")
    fig.colorbar(image, ax=ax, shrink=0.85, label=r"$\Delta \eta_{\mathrm{best}}$")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return {
        labels[i]: {labels[j]: float(matrix[i, j]) for j in range(len(labels))}
        for i in range(len(labels))
    }


def _write_markdown_table(path: Path, rows: list[dict[str, object]]) -> None:
    headers = [
        "case",
        "group",
        "topology",
        "best_regime",
        "eta_best_mean",
        "eta_best_std",
        "gamma_best",
        "coherence_best_mean",
        "loss_best_mean",
        "final_purity_mean",
        "final_entropy_mean",
        "final_population_entropy_mean",
        "final_participation_ratio_mean",
        "final_ipr_mean",
        "trace_dev_max",
        "closure_err_max",
        "min_eig",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(
                [
                    str(row["case"]),
                    str(row["group"]),
                    str(row["topology"]),
                    str(row["best_regime"]),
                    f"{row['eta_best_mean']:.6f}",
                    f"{row['eta_best_std']:.6f}",
                    f"{row['gamma_best']:.6f}",
                    f"{row['coherence_best_mean']:.6f}",
                    f"{row['loss_best_mean']:.6f}",
                    f"{row['final_purity_mean']:.6f}",
                    f"{row['final_entropy_mean']:.6f}",
                    f"{row['final_population_entropy_mean']:.6f}",
                    f"{row['final_participation_ratio_mean']:.6f}",
                    f"{row['final_ipr_mean']:.6f}",
                    f"{row['trace_dev_max']:.3e}",
                    f"{row['closure_err_max']:.3e}",
                    f"{row['min_eig']:.3e}",
                ]
            ) + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a detailed collection of graph-transport simulations.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_graph_collection_config.json"),
        help="Path to the graph-collection configuration file.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    raw_config, times, dephasing_rates, animation_stride, animation_fps, cases = _load_config(config_path)
    output_dir = ROOT / "outputs" / "transport_networks" / str(raw_config["output_subdir"]) / "latest"
    figure_dir = output_dir / "figures"
    animation_dir = output_dir / "animations"
    figure_dir.mkdir(parents=True, exist_ok=True)
    animation_dir.mkdir(parents=True, exist_ok=True)

    case_results = [_run_case(case, times, dephasing_rates) for case in cases]

    rows: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = {}
    results_payload: dict[str, object] = {"study_name": raw_config["study_name"], "cases": {}, "groups": {}}

    for case_result in case_results:
        case = case_result["case"]
        scenario_slug = slugify(case.name)
        grouped.setdefault(case.group, []).append(case_result)

        save_graph_topology_figure(
            figure_dir / f"{scenario_slug}_topology.png",
            scenario_name=case.name,
            adjacency=case_result["adjacency"],
            topology=case.topology,
            trap_site=case.trap_site,
            initial_site=case.initial_site,
            site_energies_hz=case_result["representative_site_energies_hz"],
            coupling_hz=case.coupling_hz,
            sink_rate_hz=case.sink_rate_hz,
            loss_rate_hz=case.loss_rate_hz,
        )
        representative = case_result["representative_run"]
        save_population_animation_gif(
            animation_dir / f"{scenario_slug}_population_evolution.gif",
            scenario_name=case.name,
            adjacency=case_result["adjacency"],
            topology=case.topology,
            trap_site=case.trap_site,
            initial_site=case.initial_site,
            states=representative["simulation"].states,
            sink_population=representative["simulation"].sink_population,
            loss_population=representative["simulation"].loss_population,
            times=representative["simulation"].times,
            dephasing_rate_hz=case_result["best_rate_hz"],
            stride=animation_stride,
            fps=animation_fps,
            site_energies_hz=representative["site_energies_hz"],
            coupling_hz=case.coupling_hz,
            sink_rate_hz=case.sink_rate_hz,
            loss_rate_hz=case.loss_rate_hz,
        )

        rows.append(
            {
                "case": case.name,
                "group": case.group,
                "topology": case.topology,
                "best_regime": case_result["best_regime"],
                "eta_best_mean": float(case_result["efficiency_mean"][case_result["best_idx"]]),
                "eta_best_std": float(case_result["efficiency_std"][case_result["best_idx"]]),
                "gamma_best": float(case_result["best_rate_hz"]),
                "coherence_best_mean": float(case_result["coherence_mean"][case_result["best_idx"]]),
                "loss_best_mean": float(case_result["best_loss_mean"]),
                "final_purity_mean": float(case_result["final_purity_mean"]),
                "final_entropy_mean": float(case_result["final_entropy_mean"]),
                "final_population_entropy_mean": float(case_result["final_population_entropy_mean"]),
                "final_participation_ratio_mean": float(case_result["final_participation_ratio_mean"]),
                "final_ipr_mean": float(case_result["final_ipr_mean"]),
                "trace_dev_max": float(case_result["best_rate_diagnostics"]["max_trace_deviation"]),
                "closure_err_max": float(case_result["best_rate_diagnostics"]["max_population_closure_error"]),
                "min_eig": float(case_result["best_rate_diagnostics"]["min_state_eigenvalue"]),
            }
        )
        results_payload["cases"][case.name] = {
            "group": case.group,
            "topology": case.topology,
            "n_sites": case.n_sites,
            "n_realizations": len(case.seeds),
            "coupling_hz": case.coupling_hz,
            "sink_rate_hz": case.sink_rate_hz,
            "loss_rate_hz": case.loss_rate_hz,
            "initial_site": case.initial_site,
            "trap_site": case.trap_site,
            "disorder_strength_hz": case.disorder_strength_hz,
            "seeds": list(case.seeds),
            "best_regime": case_result["best_regime"],
            "best_rate_hz": case_result["best_rate_hz"],
            "efficiency_mean": case_result["efficiency_mean"].tolist(),
            "efficiency_std": case_result["efficiency_std"].tolist(),
            "coherence_mean": case_result["coherence_mean"].tolist(),
            "coherence_std": case_result["coherence_std"].tolist(),
            "loss_mean": case_result["loss_mean"].tolist(),
            "loss_std": case_result["loss_std"].tolist(),
            "purity_mean_t": case_result["purity_mean_t"].tolist(),
            "purity_std_t": case_result["purity_std_t"].tolist(),
            "entropy_mean_t": case_result["entropy_mean_t"].tolist(),
            "entropy_std_t": case_result["entropy_std_t"].tolist(),
            "population_entropy_mean_t": case_result["population_entropy_mean_t"].tolist(),
            "population_entropy_std_t": case_result["population_entropy_std_t"].tolist(),
            "participation_ratio_mean_t": case_result["participation_ratio_mean_t"].tolist(),
            "participation_ratio_std_t": case_result["participation_ratio_std_t"].tolist(),
            "ipr_mean_t": case_result["ipr_mean_t"].tolist(),
            "ipr_std_t": case_result["ipr_std_t"].tolist(),
            "final_purity_mean": case_result["final_purity_mean"],
            "final_purity_std": case_result["final_purity_std"],
            "final_entropy_mean": case_result["final_entropy_mean"],
            "final_entropy_std": case_result["final_entropy_std"],
            "final_population_entropy_mean": case_result["final_population_entropy_mean"],
            "final_population_entropy_std": case_result["final_population_entropy_std"],
            "final_participation_ratio_mean": case_result["final_participation_ratio_mean"],
            "final_participation_ratio_std": case_result["final_participation_ratio_std"],
            "final_ipr_mean": case_result["final_ipr_mean"],
            "final_ipr_std": case_result["final_ipr_std"],
            "best_rate_diagnostics": case_result["best_rate_diagnostics"],
            "representative_site_energies_hz": np.asarray(case_result["representative_site_energies_hz"], dtype=float).tolist(),
        }

    for group_name, cases_in_group in grouped.items():
        _plot_group_curves(figure_dir / f"{group_name}_sink_efficiency.png", group_name, "efficiency", r"Sink efficiency $\eta(T)$", dephasing_rates, cases_in_group)
        _plot_group_curves(figure_dir / f"{group_name}_coherence.png", group_name, "coherence", r"Mean coherence $C_{\ell_1}$", dephasing_rates, cases_in_group)
        _plot_population_group(figure_dir / f"{group_name}_population_dynamics.png", group_name, cases_in_group, times)
        _plot_statmech_group(figure_dir / f"{group_name}_statmech_observables.png", group_name, cases_in_group, times)
        pairwise = _plot_pairwise_heatmap(
            figure_dir / f"{group_name}_pairwise_eta_best.png",
            f"{group_name.capitalize()} cases: pairwise differences in best sink efficiency",
            cases_in_group,
        )
        results_payload["groups"][group_name] = {"pairwise_best_efficiency_difference": pairwise}

    with (output_dir / "comparative_table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    _write_markdown_table(output_dir / "comparative_table.md", rows)

    (output_dir / "results.json").write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(raw_config, indent=2), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "script": "scripts/run_transport_graph_collection.py",
                "config_path": str(config_path),
                "time_grid": {"t_final": float(times[-1]), "n_samples": int(times.size)},
                "dephasing_rates_hz": dephasing_rates.tolist(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
