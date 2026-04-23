from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
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
    enaqt_scan,
    load_transport_lab_config,
    save_graph_topology_figure,
    save_graph_topology_overview,
    save_population_animation_gif,
    site_energies_for_scenario,
    slugify,
)


def _safe_script_label() -> str:
    try:
        return str(Path(__file__).resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return "scripts/run_transport_graph_lab.py"


def _write_markdown_table(path: Path, rows: list[dict[str, object]]) -> None:
    headers = [
        "scenario",
        "topology",
        "n_sites",
        "best_regime",
        "eta_coherent",
        "eta_best",
        "gamma_best",
        "eta_high",
        "coherence_best",
        "loss_best",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scenario"]),
                    str(row["topology"]),
                    str(row["n_sites"]),
                    str(row["best_regime"]),
                    f"{row['eta_coherent']:.6f}",
                    f"{row['eta_best']:.6f}",
                    f"{row['gamma_best']:.6f}",
                    f"{row['eta_high']:.6f}",
                    f"{row['coherence_best']:.6f}",
                    f"{row['loss_best']:.6f}",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_sink_note(path: Path) -> None:
    path.write_text(
        "# What the sink means\n\n"
        "In these simulations, the `sink` is an absorbing target state that represents "
        "successful transport.\n\n"
        "- It is not one more physical node of the graph.\n"
        "- It is a bookkeeping state that receives population from the chosen trap site.\n"
        "- When population reaches the sink, that part of the excitation is counted as a successful arrival.\n"
        "- The main observable `sink efficiency` is therefore the final sink population.\n\n"
        "This is useful because it separates three different things:\n\n"
        "- coherent motion inside the graph;\n"
        "- successful capture into the target channel (`sink`);\n"
        "- unwanted dissipation into the `loss` channel.\n",
        encoding="utf-8",
    )


def _annotate_main_plots(ax_eff: plt.Axes, ax_coh: plt.Axes, fig_pop: plt.Figure, axes_pop: np.ndarray) -> None:
    ax_eff.text(
        0.02,
        0.98,
        "Variables:\n"
        r"$\gamma_{\phi}$ = dephasing rate" "\n"
        r"$\eta(T)=\rho_{ss}(T)$ = sink efficiency" "\n"
        "higher curve = better transport",
        transform=ax_eff.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.92},
    )
    ax_coh.text(
        0.02,
        0.98,
        "Variables:\n"
        r"$C_{\ell_1}=\sum_{i\neq j}|\rho_{ij}|$" "\n"
        "measures site-basis coherence\n"
        "lower values mean stronger decoherence",
        transform=ax_coh.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.92},
    )
    axes_pop[0].text(
        0.02,
        0.98,
        "Variables:\n"
        r"$P_i(t)=\rho_{ii}(t)$" "\n"
        r"$P_{\mathrm{sink}}(t)$ = dashed black curve" "\n"
        "best regime shown for each graph",
        transform=axes_pop[0].transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.92},
    )
    fig_pop.text(
        0.5,
        -0.02,
        "Each panel shows the graph dynamics at the dephasing rate that maximizes sink efficiency for that scenario.",
        ha="center",
        va="top",
        fontsize=9,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run configurable graph-transport simulations.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_graph_lab_config.json"),
        help="Path to the JSON configuration file.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    config = load_transport_lab_config(config_path)

    output_dir = ROOT / "outputs" / "transport_networks" / config.output_subdir / "latest"
    figure_dir = output_dir / "figures"
    animation_dir = output_dir / "animations"
    figure_dir.mkdir(parents=True, exist_ok=True)
    animation_dir.mkdir(parents=True, exist_ok=True)

    times = np.linspace(0.0, config.t_final, config.n_time_samples)
    scenario_blocks: list[dict[str, object]] = []
    table_rows: list[dict[str, object]] = []
    metrics_payload: dict[str, object] = {"scenarios": {}}
    topology_blocks: list[dict[str, object]] = []

    fig_eff, ax_eff = plt.subplots(figsize=(8.8, 5.4))
    fig_coh, ax_coh = plt.subplots(figsize=(8.8, 5.4))
    fig_pop, axes_pop = plt.subplots(
        1,
        len(config.scenarios),
        figsize=(5.1 * len(config.scenarios), 4.4),
        sharey=True,
    )
    if len(config.scenarios) == 1:
        axes_pop = np.array([axes_pop])

    for axis, scenario in zip(axes_pop, config.scenarios, strict=True):
        adjacency = adjacency_for_topology(scenario.topology, scenario.n_sites)
        site_energies = site_energies_for_scenario(scenario)
        scan = enaqt_scan(
            adjacency=adjacency,
            coupling_hz=scenario.coupling_hz,
            dephasing_rates_hz=config.dephasing_rates_hz,
            sink_rate_hz=scenario.sink_rate_hz,
            loss_rate_hz=scenario.loss_rate_hz,
            times=times,
            initial_site=scenario.initial_site,
            trap_site=scenario.trap_site,
            site_energies_hz=site_energies,
        )

        efficiencies = np.array([case.transport_efficiency for case in scan], dtype=float)
        coherences = np.array([case.mean_coherence_l1 for case in scan], dtype=float)
        losses = np.array([case.loss_population[-1] for case in scan], dtype=float)
        best_idx = int(np.argmax(efficiencies))
        best_case = scan[best_idx]
        best_regime = classify_transport_regime(best_idx, len(config.dephasing_rates_hz))
        scenario_slug = slugify(scenario.name)

        save_graph_topology_figure(
            figure_dir / f"{scenario_slug}_topology.png",
            scenario_name=scenario.name,
            adjacency=adjacency,
            topology=scenario.topology,
            trap_site=scenario.trap_site,
            initial_site=scenario.initial_site,
            site_energies_hz=site_energies,
            coupling_hz=scenario.coupling_hz,
            sink_rate_hz=scenario.sink_rate_hz,
            loss_rate_hz=scenario.loss_rate_hz,
        )
        save_population_animation_gif(
            animation_dir / f"{scenario_slug}_population_evolution.gif",
            scenario_name=scenario.name,
            adjacency=adjacency,
            topology=scenario.topology,
            trap_site=scenario.trap_site,
            initial_site=scenario.initial_site,
            states=best_case.states,
            sink_population=best_case.sink_population,
            loss_population=best_case.loss_population,
            times=best_case.times,
            dephasing_rate_hz=float(config.dephasing_rates_hz[best_idx]),
            stride=config.animation_stride,
            fps=config.animation_fps,
            site_energies_hz=site_energies,
            coupling_hz=scenario.coupling_hz,
            sink_rate_hz=scenario.sink_rate_hz,
            loss_rate_hz=scenario.loss_rate_hz,
        )

        ax_eff.plot(config.dephasing_rates_hz, efficiencies, marker="o", lw=1.6, label=scenario.name)
        ax_coh.plot(config.dephasing_rates_hz, coherences, marker="o", lw=1.6, label=scenario.name)

        for site in range(scenario.n_sites):
            axis.plot(
                best_case.times,
                np.real(best_case.states[:, site, site]),
                lw=1.3,
                label=fr"$P_{{{site}}}(t)$",
            )
        axis.plot(
            best_case.times,
            best_case.sink_population,
            lw=2.0,
            ls="--",
            color="black",
            label=r"$P_{\mathrm{sink}}(t)$",
        )
        axis.set_title(f"{scenario.name}\n(best regime: {best_regime})")
        axis.set_xlabel("Time (arb. units)")
        axis.grid(alpha=0.2)

        scenario_blocks.append(
            {
                "scenario": asdict(scenario),
                "site_energies_hz": site_energies.tolist(),
                "best_regime": best_regime,
                "best_dephasing_rate_hz": float(config.dephasing_rates_hz[best_idx]),
                "transport_efficiency": efficiencies.tolist(),
                "mean_coherence_l1": coherences.tolist(),
                "final_loss_population": losses.tolist(),
                "topology_figure": str((figure_dir / f"{scenario_slug}_topology.png").relative_to(ROOT)),
                "population_animation_gif": str((animation_dir / f"{scenario_slug}_population_evolution.gif").relative_to(ROOT)),
            }
        )
        metrics_payload["scenarios"][scenario.name] = {
            "efficiency_no_dephasing": float(efficiencies[0]),
            "efficiency_optimal_dephasing": float(efficiencies[best_idx]),
            "efficiency_high_dephasing": float(efficiencies[-1]),
            "optimal_dephasing_rate_hz": float(config.dephasing_rates_hz[best_idx]),
            "best_regime": best_regime,
            "enaqt_gain_over_coherent": float(efficiencies[best_idx] - efficiencies[0]),
            "high_dephasing_penalty": float(efficiencies[best_idx] - efficiencies[-1]),
            "mean_coherence_at_optimum": float(coherences[best_idx]),
            "final_sink_population_at_optimum": float(best_case.sink_population[-1]),
            "final_loss_population_at_optimum": float(best_case.loss_population[-1]),
            "max_trace_deviation_at_optimum": float(best_case.max_trace_deviation),
            "max_population_closure_error_at_optimum": float(best_case.max_population_closure_error),
            "min_state_eigenvalue_at_optimum": float(best_case.min_state_eigenvalue),
        }
        table_rows.append(
            {
                "scenario": scenario.name,
                "topology": scenario.topology,
                "n_sites": scenario.n_sites,
                "best_regime": best_regime,
                "eta_coherent": float(efficiencies[0]),
                "eta_best": float(efficiencies[best_idx]),
                "gamma_best": float(config.dephasing_rates_hz[best_idx]),
                "eta_high": float(efficiencies[-1]),
                "coherence_best": float(coherences[best_idx]),
                "loss_best": float(best_case.loss_population[-1]),
            }
        )
        topology_blocks.append(
            {
                "name": scenario.name,
                "topology": scenario.topology,
                "adjacency": adjacency.tolist(),
                "trap_site": scenario.trap_site,
                "initial_site": scenario.initial_site,
            }
        )

    ax_eff.set_xlabel(r"Dephasing rate $\gamma_\phi$ (arb. units)")
    ax_eff.set_ylabel(r"Sink efficiency $\eta(T)$")
    ax_eff.set_title("Sink efficiency by graph")
    ax_eff.grid(alpha=0.2)
    ax_eff.legend(frameon=False)

    ax_coh.set_xlabel(r"Dephasing rate $\gamma_\phi$ (arb. units)")
    ax_coh.set_ylabel(r"Mean coherence $C_{\ell_1}$")
    ax_coh.set_title("Coherence by graph")
    ax_coh.grid(alpha=0.2)
    ax_coh.legend(frameon=False)
    fig_coh.tight_layout()

    axes_pop[0].set_ylabel("Population")
    axes_pop[0].legend(frameon=False, fontsize=8)
    fig_pop.suptitle("Population dynamics in the best regime of each graph", y=1.03)

    _annotate_main_plots(ax_eff, ax_coh, fig_pop, axes_pop)
    fig_eff.tight_layout()
    fig_pop.tight_layout()

    fig_eff.savefig(figure_dir / "sink_efficiency_by_graph.png", dpi=220, bbox_inches="tight")
    fig_coh.savefig(figure_dir / "coherence_by_graph.png", dpi=220, bbox_inches="tight")
    fig_pop.savefig(figure_dir / "population_dynamics_by_graph.png", dpi=220, bbox_inches="tight")
    save_graph_topology_overview(figure_dir / "graph_topology_overview.png", topology_blocks)
    plt.close(fig_eff)
    plt.close(fig_coh)
    plt.close(fig_pop)

    results_payload = {
        "study_name": config.study_name,
        "dephasing_rates_hz": config.dephasing_rates_hz.tolist(),
        "times": {"t_final": float(times[-1]), "n_samples": int(times.size)},
        "visualization": {
            "animation_stride": config.animation_stride,
            "animation_fps": config.animation_fps,
        },
        "scenarios": scenario_blocks,
    }
    config_used = {
        "study_name": config.study_name,
        "output_subdir": config.output_subdir,
        "time_grid": {"t_final": config.t_final, "n_samples": config.n_time_samples},
        "visualization": {
            "animation_stride": config.animation_stride,
            "animation_fps": config.animation_fps,
        },
        "dephasing_rates_hz": config.dephasing_rates_hz.tolist(),
        "scenarios": [asdict(scenario) for scenario in config.scenarios],
    }
    run_metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "script": _safe_script_label(),
        "config_path": str(config_path),
        "output_dir": str(output_dir.relative_to(ROOT)),
    }

    csv_path = output_dir / "comparative_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table_rows[0].keys()))
        writer.writeheader()
        writer.writerows(table_rows)

    _write_markdown_table(output_dir / "comparative_table.md", table_rows)
    _write_sink_note(output_dir / "SINK_EXPLANATION.md")
    (output_dir / "results.json").write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config_used, indent=2), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
