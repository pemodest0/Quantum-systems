from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def _src(text: str) -> list[str]:
    text = dedent(text).strip("\n")
    return [line + "\n" for line in text.splitlines()]


def _md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _src(text)}


def _code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _src(text),
    }


def _metadata(name: str) -> dict:
    return {
        "colab": {"name": name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
    }


def _write_notebook(path: Path, cells: list[dict], name: str) -> None:
    notebook = {"cells": cells, "metadata": _metadata(name), "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")


def build_foundations_notebook() -> None:
    path = NOTEBOOKS / "colab_transport_tutorial_from_graph_to_lab.ipynb"
    cells = [
        _md(
            """
            # Open Quantum Transport on Networks: From the Smallest Graph to the Current Lab

            [Open in Colab](https://colab.research.google.com/github/pemodest0/Quantum-systems/blob/main/notebooks/colab_transport_tutorial_from_graph_to_lab.ipynb)

            This notebook is the **teaching and presentation notebook**.

            It starts from the minimal graph picture, explains what the excitation, sink, loss, disorder, and dephasing mean, and then runs small clean simulations with **only three helper files**:

            - `notebooks/colab_transport_review/transport_core.py`
            - `notebooks/colab_transport_review/transport_cases.py`
            - `notebooks/colab_transport_review/transport_repo.py`

            What this notebook is:

            - a **classical numerical simulation** of an effective open quantum system;
            - a clean path from simple examples to the current research questions;
            - a presentation notebook that can be shown to a professor.

            What this notebook is not:

            - not a quantum-computer run;
            - not a microscopic material simulation;
            - not the full heavy atlas campaign.
            """
        ),
        _md(
            """
            ## How to use this notebook

            1. Run the setup cell.
            2. Run the notebook from top to bottom.
            3. Use the small examples first.
            4. Only after that jump to the cells that load the real lab outputs.

            The examples here are intentionally small enough to run quickly in Colab.
            """
        ),
        _code(
            """
            %pip -q install numpy scipy pandas matplotlib networkx

            import inspect
            import os
            import subprocess
            import sys
            from pathlib import Path

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            from IPython.display import Markdown, display

            ROOT = Path("/content/Quantum-systems")
            if not ROOT.exists():
                subprocess.run(["git", "clone", "https://github.com/pemodest0/Quantum-systems.git", str(ROOT)], check=True)

            os.chdir(ROOT)
            if str(ROOT / "notebooks") not in sys.path:
                sys.path.insert(0, str(ROOT / "notebooks"))

            from colab_transport_review import (
                choose_target,
                current_research_snapshot,
                dephasing_scan,
                draw_graph,
                make_graph,
                mini_seeded_campaign,
                quantum_vs_classical_case,
                reference_rows,
                simulate_open_quantum_transport,
                target_placement_scan,
            )
            from colab_transport_review import transport_cases, transport_core, transport_repo

            plt.rcParams.update(
                {
                    "figure.figsize": (8, 4.8),
                    "axes.grid": True,
                    "grid.alpha": 0.25,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                }
            )
            np.set_printoptions(precision=4, suppress=True)

            print(f"Repository root: {ROOT}")
            """
        ),
        _md(
            """
            ## 1. What the model means physically

            We use an **effective one-excitation open-system model**.

            - A **node** is a local quantum site.
            - An **edge** is coherent hopping between two sites.
            - The **excitation** is one packet of quantum amplitude placed on one node at the start.
            - The **sink** is an absorbing target channel attached to one chosen node.
            - **Loss** removes excitation from the graph without sending it to the target.
            - **Disorder** means random onsite energy offsets.
            - **Dephasing** means phase scrambling by the environment.

            Central diagnostic:

            \\
            S(\\rho_g) = -\\mathrm{Tr}(\\rho_g \\log \\rho_g)
            \\

            Here `rho_g` is the **graph-normalized remaining state on the graph**. This von Neumann entropy measures **mixing on the graph**, not transport success by itself.
            """
        ),
        _code(
            """
            display(Markdown("### The three code files used in this notebook"))
            for module in [transport_core, transport_cases, transport_repo]:
                path = Path(module.__file__)
                text = path.read_text(encoding="utf-8")
                print(f"\\n{'=' * 90}\\n{path.relative_to(ROOT)}\\n{'=' * 90}")
                print(f"{len(text.splitlines())} lines")
            """
        ),
        _md("## 2. Graph gallery"),
        _code(
            """
            gallery_families = [
                "chain", "ring", "star", "complete",
                "square_lattice_2d", "bottleneck", "clustered", "modular_two_community",
                "random_geometric", "erdos_renyi", "watts_strogatz_small_world", "barabasi_albert_scale_free",
                "sierpinski_gasket", "sierpinski_carpet_like",
            ]

            ncols = 4
            nrows = int(np.ceil(len(gallery_families) / ncols))
            fig, axes = plt.subplots(nrows, ncols, figsize=(15, 3.2 * nrows))
            axes = axes.flatten()

            for ax, family in zip(axes, gallery_families):
                graph, pos = make_graph(family, n=10, seed=11)
                initial_site = min(graph.nodes)
                target_site = max(graph.nodes)
                draw_graph(graph, pos, initial_site=initial_site, target_site=target_site, title=family, ax=ax)

            for ax in axes[len(gallery_families):]:
                ax.axis("off")

            plt.tight_layout()
            plt.show()
            """
        ),
        _md(
            """
            ## 3. First experiment: one excitation on a chain

            This is the simplest useful example:

            - the excitation starts on the left;
            - the target is on the right;
            - we add a moderate amount of disorder and dephasing;
            - we monitor target arrival, graph population, loss, entropy, and purity.
            """
        ),
        _code(
            """
            graph, pos = make_graph("chain", n=6, seed=3)
            initial_site = 0
            target_site = 5

            quantum, node_pop = simulate_open_quantum_transport(
                graph,
                pos,
                initial_site=initial_site,
                target_site=target_site,
                disorder_strength_over_J=0.3,
                gamma_phi_over_J=0.1,
                seed=3,
                t_final=12,
                n_times=140,
            )

            fig, axes = plt.subplots(2, 2, figsize=(14, 8))
            draw_graph(graph, pos, initial_site=initial_site, target_site=target_site, title="Chain: initial site 0, target site 5", ax=axes[0, 0])

            axes[0, 1].plot(quantum["time"], node_pop)
            axes[0, 1].set_title("Population on graph sites")
            axes[0, 1].set_xlabel("time")
            axes[0, 1].set_ylabel("population")

            axes[1, 0].plot(quantum["time"], quantum["target_arrival"], label="target arrival", color="#d62728")
            axes[1, 0].plot(quantum["time"], quantum["loss"], label="loss", color="#555555")
            axes[1, 0].plot(quantum["time"], quantum["graph_population"], label="still in graph", color="#1f77b4")
            axes[1, 0].set_title("Population closure")
            axes[1, 0].set_xlabel("time")
            axes[1, 0].set_ylabel("probability")
            axes[1, 0].legend()

            axes[1, 1].plot(quantum["time"], quantum["von_neumann_entropy"], label="von Neumann entropy", color="#2ca02c")
            axes[1, 1].plot(quantum["time"], quantum["purity"], label="purity", color="#9467bd")
            axes[1, 1].set_title("Mixing diagnostics")
            axes[1, 1].set_xlabel("time")
            axes[1, 1].legend()

            plt.tight_layout()
            plt.show()

            quantum.tail()
            """
        ),
        _md(
            """
            ### How to read the chain plots

            - **Target arrival** is the useful quantity: how much reached the target channel.
            - **Loss** is useless transport: excitation that disappeared before reaching the target.
            - **Graph population** is what still remains on the graph.
            - **Von Neumann entropy** tells you how mixed the graph state is.
            - **Purity** falls as the state becomes more mixed.

            Entropy going up is **not automatically good**. It can happen together with good transport, bad transport, or simple spreading.
            """
        ),
        _md("## 4. Phase scrambling scan"),
        _code(
            """
            scan = pd.concat(
                [dephasing_scan(family, n=8, W=0.6, seed=3)[0] for family in ["chain", "ring", "complete", "star"]],
                ignore_index=True,
            )

            fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
            for family, group in scan.groupby("family"):
                axes[0].plot(group["gamma_phi_over_J"], group["target_arrival"], marker="o", label=family)
                axes[1].plot(group["gamma_phi_over_J"], group["von_neumann_entropy"], marker="o", label=family)

            axes[0].set_title("Target arrival versus phase scrambling")
            axes[0].set_xlabel("gamma_phi / J")
            axes[0].set_ylabel("target arrival")
            axes[0].legend()

            axes[1].set_title("Final graph-normalized von Neumann entropy")
            axes[1].set_xlabel("gamma_phi / J")
            axes[1].set_ylabel("entropy")
            axes[1].legend()

            plt.tight_layout()
            plt.show()

            scan.groupby("family")[["target_arrival", "gain_over_zero_dephasing", "von_neumann_entropy", "purity"]].max().round(4)
            """
        ),
        _md(
            """
            The physical question here is **not** “does entropy increase?”.

            The correct question is:

            **Does a nonzero dephasing rate increase useful arrival at the target compared with the zero-dephasing case?**
            """
        ),
        _md("## 5. Same graph, different target"),
        _code(
            """
            placement, ring_graph, ring_pos, ring_initial = target_placement_scan(
                "ring",
                n=8,
                target_styles=("near", "far", "high_centrality", "low_centrality"),
                W=0.6,
                gamma=0.1,
                seed=3,
            )

            fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
            draw_graph(
                ring_graph,
                ring_pos,
                initial_site=ring_initial,
                target_site=int(placement.loc[placement["target_style"] == "far", "target_site"].iloc[0]),
                title="Ring example with one highlighted target",
                ax=axes[0],
            )
            axes[1].bar(placement["target_style"], placement["target_arrival"], color="#4c78a8")
            axes[1].set_title("Target arrival for different target placements")
            axes[1].set_ylabel("target arrival")
            axes[1].tick_params(axis="x", rotation=20)
            plt.tight_layout()
            plt.show()

            placement[["target_style", "target_site", "target_arrival", "von_neumann_entropy", "target_degree", "shortest_path_distance", "target_closeness"]].round(4)
            """
        ),
        _md(
            """
            This is one of the central ideas of the project:

            **the same network can behave very differently when only the target position changes**.
            """
        ),
        _md("## 6. Quantum versus classical control"),
        _code(
            """
            merged, summary, qc_graph, qc_pos, qc_initial, qc_target = quantum_vs_classical_case(
                "ring",
                n=8,
                W=0.6,
                gamma=0.1,
                seed=3,
                target_style="far",
            )

            fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
            draw_graph(qc_graph, qc_pos, initial_site=qc_initial, target_site=qc_target, title="Same graph, same initial site, same target", ax=axes[0])
            axes[1].plot(merged["time"], merged["target_arrival"], label="open quantum model", color="#1f77b4")
            axes[1].plot(merged["time"], merged["target_arrival_classical"], label="classical rate model", color="#ff7f0e")
            axes[1].set_title("Target arrival: quantum versus classical")
            axes[1].set_xlabel("time")
            axes[1].set_ylabel("target arrival")
            axes[1].legend()
            plt.tight_layout()
            plt.show()

            pd.DataFrame([summary]).round(4)
            """
        ),
        _md(
            """
            A classical control prevents a false claim.

            If the classical model reaches the target equally well, then the result is mostly a **network-connectivity effect**, not a specifically quantum one.
            """
        ),
        _md("## 7. Small seeded campaign"),
        _code(
            """
            campaign = mini_seeded_campaign(
                families=("chain", "ring", "star", "complete"),
                n=8,
                seeds=(3, 5, 7, 11),
                gamma_values=(0.0, 0.05, 0.1, 0.2, 0.4),
                W=0.6,
            )

            summary = campaign.groupby("family", as_index=False).agg(
                arrival_mean=("target_arrival", "mean"),
                entropy_mean=("von_neumann_entropy", "mean"),
                purity_mean=("purity", "mean"),
                best_gain=("gain_over_zero_dephasing", "max"),
            )
            summary = summary.sort_values("arrival_mean", ascending=False)

            fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
            axes[0].bar(summary["family"], summary["arrival_mean"], color="#4c78a8")
            axes[0].set_title("Mean target arrival")
            axes[0].tick_params(axis="x", rotation=25)

            axes[1].bar(summary["family"], summary["entropy_mean"], color="#72b7b2")
            axes[1].set_title("Mean final von Neumann entropy")
            axes[1].tick_params(axis="x", rotation=25)

            axes[2].bar(summary["family"], summary["best_gain"], color="#54a24b")
            axes[2].axhline(0.05, color="black", linestyle="--", linewidth=1)
            axes[2].set_title("Best dephasing gain over zero-noise")
            axes[2].tick_params(axis="x", rotation=25)

            plt.tight_layout()
            plt.show()

            summary.round(4)
            """
        ),
        _md("## 8. Load the real lab state"),
        _code(
            """
            snapshot = current_research_snapshot(ROOT)
            evidence_metrics = snapshot["evidence_prep_metrics"]
            journey_metrics = snapshot["research_journey_metrics"]
            classification_metrics = snapshot["classification_metrics"]

            display(Markdown("### Evidence-prep atlas metrics"))
            display(pd.DataFrame([evidence_metrics]))

            display(Markdown("### Research journey metrics"))
            display(pd.DataFrame([journey_metrics]))

            display(Markdown("### Network classification metrics"))
            display(pd.DataFrame([classification_metrics]))
            """
        ),
        _md(
            """
            ## 9. What is already strong and what is still open

            Already strong enough to discuss:

            - target placement matters;
            - some graph families show positive quantum-minus-classical arrival;
            - moderate dephasing can improve useful arrival in selected regimes;
            - entropy and purity work well as diagnostics of mixing.

            Still open:

            - the full strong atlas is not finished yet;
            - the intense atlas is not the right run for a mixed-use machine;
            - not every family boundary is resolved;
            - entropy must never be sold as transport success by itself.
            """
        ),
        _md("## 10. References"),
        _code(
            """
            refs = reference_rows()
            refs
            """
        ),
    ]
    _write_notebook(path, cells, "Open Quantum Transport Tutorial From Graph to Lab")


def build_review_notebook() -> None:
    path = NOTEBOOKS / "colab_transport_research_review.ipynb"
    cells = [
        _md(
            """
            # Open Quantum Transport Research Review

            [Open in Colab](https://colab.research.google.com/github/pemodest0/Quantum-systems/blob/main/notebooks/colab_transport_research_review.ipynb)

            This notebook is the **research-review notebook**.

            It does not try to rerun the heavy campaigns. Instead, it reads the current project outputs directly from the repository and organizes the current evidence in a presentation-friendly way.
            """
        ),
        _md(
            """
            ## What this notebook covers

            - the evidence-prep atlas;
            - the integrated research journey;
            - the paper reproduction suite;
            - the current graph-classification result;
            - the current paused state of the strong atlas.
            """
        ),
        _code(
            """
            %pip -q install pandas matplotlib

            import os
            import subprocess
            import sys
            from pathlib import Path

            import pandas as pd
            from IPython.display import Image, Markdown, display

            ROOT = Path("/content/Quantum-systems")
            if not ROOT.exists():
                subprocess.run(["git", "clone", "https://github.com/pemodest0/Quantum-systems.git", str(ROOT)], check=True)

            os.chdir(ROOT)
            if str(ROOT / "notebooks") not in sys.path:
                sys.path.insert(0, str(ROOT / "notebooks"))

            from colab_transport_review import (
                current_research_snapshot,
                professor_talking_points,
                reference_rows,
                resolve_repo_root,
            )

            TRANSPORT = resolve_repo_root(ROOT) / "outputs" / "transport_networks"
            snapshot = current_research_snapshot(ROOT)
            print(f"Repository root: {ROOT}")
            """
        ),
        _md("## 1. High-level snapshot"),
        _code(
            """
            evidence_metrics = snapshot["evidence_prep_metrics"]
            journey_metrics = snapshot["research_journey_metrics"]
            classification_metrics = snapshot["classification_metrics"]

            snapshot_table = pd.DataFrame(
                [
                    {
                        "bundle": "evidence_prep",
                        "record_count": evidence_metrics.get("record_count"),
                        "mean_best_arrival": evidence_metrics.get("mean_best_arrival"),
                        "mean_dephasing_gain": evidence_metrics.get("mean_dephasing_gain"),
                        "mean_quantum_minus_classical": evidence_metrics.get("mean_quantum_minus_classical"),
                    },
                    {
                        "bundle": "research_journey_v2",
                        "record_count": journey_metrics.get("target_record_count"),
                        "target_spread_mean": journey_metrics.get("target_spread_mean"),
                        "mean_quantum_classical_delta": journey_metrics.get("mean_quantum_classical_delta"),
                        "classification_combined_accuracy": journey_metrics.get("classification_combined_accuracy"),
                    },
                    {
                        "bundle": "network_classification_complete",
                        "record_count": classification_metrics.get("record_count"),
                        "dynamic_accuracy": classification_metrics.get("dynamic_accuracy"),
                        "topology_accuracy": classification_metrics.get("topology_accuracy"),
                        "combined_accuracy": classification_metrics.get("combined_accuracy"),
                    },
                ]
            )
            snapshot_table
            """
        ),
        _md("## 2. Evidence-prep atlas"),
        _code(
            """
            evidence_table = snapshot["evidence_prep_table"].sort_values("best_arrival_mean", ascending=False)
            evidence_table.head(10)
            """
        ),
        _code(
            """
            for name in [
                "atlas_dashboard.png",
                "arrival_by_family_heatmap.png",
                "entropy_coherence_panel.png",
                "quantum_minus_classical_map.png",
            ]:
                display(Markdown(f"### {name}"))
                display(Image(filename=str(TRANSPORT / "dynamic_network_atlas_evidence_prep" / "latest" / "figures" / name)))
            """
        ),
        _md(
            """
            Reading rule:

            - high target arrival is good;
            - positive quantum-minus-classical is evidence in favor of specifically quantum open transport;
            - high entropy alone is not transport success.
            """
        ),
        _md("## 3. Integrated research journey"),
        _code(
            """
            pd.DataFrame([journey_metrics]).T.rename(columns={0: "value"})
            """
        ),
        _code(
            """
            for name in [
                "target_position_effect_map.png",
                "quantum_vs_classical_delta_map.png",
                "classification_article_panel.png",
                "fractal_msd_and_geometry.png",
            ]:
                display(Markdown(f"### {name}"))
                display(Image(filename=str(TRANSPORT / "research_journey_v2" / "latest" / "figures" / name)))
            """
        ),
        _md("## 4. Paper reproduction suite"),
        _code(
            """
            paper_verdicts = snapshot["paper_verdicts"]
            paper_verdicts
            """
        ),
        _code(
            """
            for name in [
                "paper_verdict_overview.png",
                "dephasing_gain_with_ci.png",
                "target_placement_with_controls.png",
                "quantum_vs_classical_arrival.png",
            ]:
                display(Markdown(f"### {name}"))
                display(Image(filename=str(TRANSPORT / "paper_reproduction_suite" / "latest" / "figures" / name)))
            """
        ),
        _md(
            """
            Important nuance:

            - `matched` means the lab reproduced the **qualitative trend or control logic** of the paper;
            - it does **not** mean exact microscopic reproduction of the original experiment.
            """
        ),
        _md("## 5. Network classification result"),
        _code(
            """
            pd.DataFrame([classification_metrics]).T.rename(columns={0: "value"})
            """
        ),
        _code(
            """
            for name in [
                "accuracy_by_feature_set.png",
                "combined_confusion_matrix.png",
                "combined_feature_importance.png",
            ]:
                display(Markdown(f"### {name}"))
                display(Image(filename=str(TRANSPORT / "network_classification_complete" / "latest" / "figures" / name)))
            """
        ),
        _md("## 6. Current strong atlas handoff state"),
        _code(
            """
            atlas_state = snapshot["atlas_state"]
            print(atlas_state["handoff_text"][:4000] if atlas_state["handoff_text"] else "No handoff state file found.")
            """
        ),
        _code(
            """
            pd.DataFrame(
                [
                    {
                        "metrics_profile": atlas_state["metrics"].get("profile"),
                        "metrics_record_count": atlas_state["metrics"].get("record_count"),
                        "run_metadata_record_count": atlas_state["run_metadata"].get("record_count"),
                        "note": "atlas_metrics can lag behind atlas_records if a chunk was interrupted before summary-writing",
                    }
                ]
            )
            """
        ),
        _md("## 7. What I would say to the professor"),
        _code(
            """
            for line in professor_talking_points():
                print("-", line)
            """
        ),
        _md("## 8. References actually driving the project"),
        _code(
            """
            reference_rows()
            """
        ),
    ]
    _write_notebook(path, cells, "Open Quantum Transport Research Review")


def main() -> None:
    build_foundations_notebook()
    build_review_notebook()
    print("Built:")
    print(" - notebooks/colab_transport_tutorial_from_graph_to_lab.ipynb")
    print(" - notebooks/colab_transport_research_review.ipynb")


if __name__ == "__main__":
    main()
