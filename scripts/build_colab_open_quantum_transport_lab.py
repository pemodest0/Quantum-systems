from __future__ import annotations

import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "colab_open_quantum_transport_lab.ipynb"
COLAB_GITHUB_LINK = (
    "https://colab.research.google.com/github/pemodest0/Quantum-systems/blob/main/"
    "notebooks/colab_open_quantum_transport_lab.ipynb"
)


def _clean(source: str) -> str:
    return textwrap.dedent(source).strip("\n")


def _markdown(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": _clean(source).splitlines(keepends=True),
    }


def _code(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _clean(source).splitlines(keepends=True),
    }


def _intro_cells() -> list[dict[str, object]]:
    return [
        _markdown(
            r"""
            # Open Quantum Transport on Graphs

            **A clean Google Colab notebook from the minimal model to the current lab results.**

            This notebook starts from the simplest graph, builds the open quantum transport model, measures von Neumann entropy, compares graph families, and then shows the evidence-prep results already produced by the lab.

            Scope:

            - This is not a quantum-computer run.
            - This is a **classical numerical simulation** of an effective open quantum system.
            - A future quantum device or superconducting circuit could implement related dynamics, but this notebook evolves density matrices on a normal computer.
            """
        ),
        _markdown(
            r"""
            ## 0. Colab setup

            Run the cells from top to bottom. The default simulations are small enough for a presentation notebook. The heavier local campaign summary is embedded later as a reference table.
            """
        ),
        _code(
            r"""
            # If Colab reports a missing package, uncomment this line:
            # !pip -q install numpy scipy pandas matplotlib networkx

            import math
            import warnings

            import matplotlib.pyplot as plt
            import networkx as nx
            import numpy as np
            import pandas as pd
            from scipy.sparse.linalg import expm_multiply

            warnings.filterwarnings("ignore", category=UserWarning)
            np.set_printoptions(precision=4, suppress=True)
            plt.rcParams.update({
                "figure.figsize": (8, 4.8),
                "axes.grid": True,
                "grid.alpha": 0.25,
                "axes.spines.top": False,
                "axes.spines.right": False,
            })
            """
        ),
        _markdown(
            r"""
            ## 1. Physical meaning

            We use a one-excitation effective model.

            - A **node** is a local quantum site: a qubit, chromophore, mode, or tight-binding site.
            - An **edge** is coherent hopping between two sites.
            - The **excitation** is one unit of quantum amplitude initially placed on one node.
            - The **target channel** is an absorbing arrival channel attached to a chosen target node.
            - **Loss** is an absorbing channel that removes excitation from any site.
            - **Phase scrambling** means local dephasing: it destroys phase information without directly moving population.
            - **Disorder** means random local energy offsets on the graph sites.

            Central entropy diagnostic:

            \[
            S(\rho_g) = -\mathrm{Tr}(\rho_g \log \rho_g).
            \]

            Here \(\rho_g\) is the density matrix restricted to the graph sites and normalized by the population still inside the graph. This entropy measures mixing of the remaining graph state. It is **not** the same as successful transport.
            """
        ),
    ]


def _graph_cells() -> list[dict[str, object]]:
    return [
        _markdown("## 2. Graph families"),
        _code(
            r"""
            def _circle_positions(n, radius=1.0):
                return {
                    i: np.array([
                        radius * math.cos(2 * math.pi * i / n),
                        radius * math.sin(2 * math.pi * i / n),
                    ])
                    for i in range(n)
                }


            def _relabel(graph, pos):
                mapping = {node: k for k, node in enumerate(graph.nodes())}
                graph = nx.relabel_nodes(graph, mapping)
                pos = {mapping[node]: np.asarray(value, dtype=float) for node, value in pos.items()}
                return graph, pos


            def make_graph(family="chain", n=8, seed=3):
                rng = np.random.default_rng(seed)

                if family == "chain":
                    graph = nx.path_graph(n)
                    pos = {i: np.array([i, 0.0]) for i in range(n)}
                elif family == "ring":
                    graph = nx.cycle_graph(n)
                    pos = _circle_positions(n)
                elif family == "complete":
                    graph = nx.complete_graph(n)
                    pos = _circle_positions(n)
                elif family == "star":
                    graph = nx.star_graph(n - 1)
                    pos = {0: np.array([0.0, 0.0])}
                    pos.update({i: _circle_positions(n - 1)[i - 1] for i in range(1, n)})
                elif family == "square_lattice_2d":
                    side = int(math.ceil(math.sqrt(n)))
                    graph = nx.Graph()
                    graph.add_nodes_from(range(n))
                    pos = {i: np.array([i % side, i // side], dtype=float) for i in range(n)}
                    for i in range(n):
                        if i + 1 < n and (i % side) != side - 1:
                            graph.add_edge(i, i + 1)
                        if i + side < n:
                            graph.add_edge(i, i + side)
                elif family == "bottleneck":
                    graph = nx.Graph()
                    graph.add_nodes_from(range(n))
                    left = list(range(n // 2))
                    right = list(range(n // 2, n))
                    for group in (left, right):
                        for a, b in zip(group[:-1], group[1:]):
                            graph.add_edge(a, b)
                        if len(group) > 2:
                            graph.add_edge(group[0], group[-1])
                    graph.add_edge(left[-1], right[0])
                    pos = {node: np.array([0.0, k], dtype=float) for k, node in enumerate(left)}
                    pos.update({node: np.array([3.0, k], dtype=float) for k, node in enumerate(right)})
                elif family in {"clustered", "modular_two_community"}:
                    graph = nx.Graph()
                    graph.add_nodes_from(range(n))
                    left = list(range(n // 2))
                    right = list(range(n // 2, n))
                    for group in (left, right):
                        for i in range(len(group)):
                            for j in range(i + 1, len(group)):
                                graph.add_edge(group[i], group[j])
                    graph.add_edge(left[-1], right[0])
                    if family == "modular_two_community" and len(left) > 2 and len(right) > 2:
                        graph.add_edge(left[-2], right[1])
                    pos = {}
                    for k, node in enumerate(left):
                        angle = 2 * math.pi * k / max(1, len(left))
                        pos[node] = np.array([math.cos(angle), math.sin(angle)])
                    for k, node in enumerate(right):
                        angle = 2 * math.pi * k / max(1, len(right))
                        pos[node] = np.array([3.0 + math.cos(angle), math.sin(angle)])
                elif family == "random_geometric":
                    points = {i: rng.random(2) for i in range(n)}
                    for radius in (0.40, 0.50, 0.65, 0.80):
                        graph = nx.random_geometric_graph(n, radius, pos=points, seed=seed)
                        if nx.is_connected(graph):
                            break
                    else:
                        graph = nx.path_graph(n)
                    pos = {i: np.asarray(points[i], dtype=float) for i in graph.nodes}
                elif family == "erdos_renyi":
                    for p in (0.35, 0.45, 0.55, 0.70):
                        graph = nx.erdos_renyi_graph(n, p, seed=seed)
                        if nx.is_connected(graph):
                            break
                    else:
                        graph = nx.path_graph(n)
                    pos = nx.spring_layout(graph, seed=seed)
                elif family == "watts_strogatz_small_world":
                    k = min(4, n - 1)
                    if k % 2:
                        k -= 1
                    graph = nx.watts_strogatz_graph(n, max(2, k), 0.25, seed=seed)
                    if not nx.is_connected(graph):
                        graph = nx.path_graph(n)
                    pos = nx.spring_layout(graph, seed=seed)
                elif family == "barabasi_albert_scale_free":
                    graph = nx.barabasi_albert_graph(n, max(1, min(2, n - 1)), seed=seed)
                    pos = nx.spring_layout(graph, seed=seed)
                elif family == "sierpinski_gasket":
                    graph = nx.Graph()
                    coords = {
                        0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0),
                        3: (0.5, 0.9), 4: (1.5, 0.9), 5: (1.0, 1.8),
                    }
                    graph.add_nodes_from(coords)
                    graph.add_edges_from([(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4), (3, 4), (3, 5), (4, 5)])
                    pos = {i: np.array(v, dtype=float) for i, v in coords.items()}
                elif family == "sierpinski_carpet_like":
                    coords = [(x, y) for y in range(3) for x in range(3) if not (x == 1 and y == 1)]
                    graph = nx.Graph()
                    graph.add_nodes_from(range(len(coords)))
                    pos = {i: np.array(coords[i], dtype=float) for i in range(len(coords))}
                    for i, a in enumerate(coords):
                        for j, b in enumerate(coords):
                            if i < j and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
                                graph.add_edge(i, j)
                else:
                    raise ValueError(f"Unknown family: {family}")

                return _relabel(graph, pos)


            def draw_graph(graph, pos, initial_site=None, target_site=None, title=""):
                colors = []
                for node in graph.nodes:
                    if node == initial_site:
                        colors.append("#1f77b4")
                    elif node == target_site:
                        colors.append("#d62728")
                    else:
                        colors.append("#d9d9d9")
                plt.figure(figsize=(4.2, 3.4))
                nx.draw_networkx_edges(graph, pos, alpha=0.45, width=1.8)
                nx.draw_networkx_nodes(graph, pos, node_color=colors, edgecolors="#222222", linewidths=0.8, node_size=420)
                nx.draw_networkx_labels(graph, pos, font_size=9)
                plt.title(title)
                plt.axis("equal")
                plt.axis("off")
                plt.show()


            graph, pos = make_graph("chain", n=6, seed=3)
            draw_graph(graph, pos, initial_site=0, target_site=5, title="Minimal chain: blue starts, red is the target")
            """
        ),
    ]


def _simulation_cells() -> list[dict[str, object]]:
    return [
        _markdown("## 3. Open quantum transport code"),
        _code(
            r"""
            def weighted_adjacency(graph, pos, coupling_law="fixed", length_scale=1.0):
                n = graph.number_of_nodes()
                A = np.zeros((n, n), dtype=float)
                for i, j in graph.edges:
                    if coupling_law == "fixed":
                        weight = 1.0
                    else:
                        distance = max(float(np.linalg.norm(pos[i] - pos[j])), 1e-9)
                        if coupling_law == "exponential_distance":
                            weight = math.exp(-distance / length_scale)
                        elif coupling_law == "power_law":
                            weight = 1.0 / (distance / length_scale) ** 3
                        else:
                            raise ValueError(f"Unknown coupling law: {coupling_law}")
                    A[i, j] = A[j, i] = weight
                return A


            def build_hamiltonian(A, J=1.0, disorder_strength_over_J=0.0, seed=0):
                rng = np.random.default_rng(seed)
                n = A.shape[0]
                onsite = disorder_strength_over_J * J * rng.uniform(-0.5, 0.5, size=n)
                H = J * A.astype(complex)
                H += np.diag(onsite.astype(complex))
                return H


            def jump(dim, row, col, rate):
                C = np.zeros((dim, dim), dtype=complex)
                C[row, col] = math.sqrt(rate)
                return C


            def liouvillian(H, jumps):
                dim = H.shape[0]
                I = np.eye(dim, dtype=complex)
                L = -1j * (np.kron(I, H) - np.kron(H.T, I))
                for C in jumps:
                    CdC = C.conj().T @ C
                    L += np.kron(C.conj(), C)
                    L += -0.5 * np.kron(I, CdC)
                    L += -0.5 * np.kron(CdC.T, I)
                return L


            def von_neumann_entropy(rho, eps=1e-12):
                rho = 0.5 * (rho + rho.conj().T)
                vals = np.linalg.eigvalsh(rho).real
                vals = vals[vals > eps]
                return float(-np.sum(vals * np.log(vals))) if vals.size else 0.0


            def shannon_entropy(prob, eps=1e-12):
                total = float(np.sum(prob))
                if total <= eps:
                    return 0.0
                p = np.asarray(prob, dtype=float) / total
                p = p[p > eps]
                return float(-np.sum(p * np.log(p)))


            def graph_observables(rho, n_graph, pos_array):
                graph_block = rho[:n_graph, :n_graph]
                node_pop = np.maximum(np.real(np.diag(graph_block)), 0.0)
                graph_population = float(node_pop.sum())
                if graph_population > 1e-12:
                    rho_g = graph_block / graph_population
                    p_g = node_pop / graph_population
                else:
                    rho_g = graph_block
                    p_g = np.zeros(n_graph)

                offdiag = rho_g - np.diag(np.diag(rho_g))
                mean_position = p_g @ pos_array if p_g.sum() > 0 else np.zeros(2)
                msd = float(np.sum(p_g * np.sum((pos_array - mean_position) ** 2, axis=1))) if p_g.sum() > 0 else 0.0
                ipr = float(np.sum(p_g ** 2))
                return {
                    "node_populations": node_pop,
                    "graph_population": graph_population,
                    "von_neumann_entropy": von_neumann_entropy(rho_g),
                    "purity": float(np.real(np.trace(rho_g @ rho_g))),
                    "coherence_l1": float(np.sum(np.abs(offdiag))),
                    "population_shannon_entropy": shannon_entropy(p_g),
                    "participation_ratio": float(1.0 / ipr) if ipr > 1e-12 else 0.0,
                    "ipr": ipr,
                    "msd": msd,
                }


            def simulate_open_quantum_transport(
                graph,
                pos,
                initial_site,
                target_site,
                disorder_strength_over_J=0.0,
                gamma_phi_over_J=0.1,
                seed=0,
                J=1.0,
                sink_rate_over_J=0.65,
                loss_rate_over_J=0.02,
                t_final=12.0,
                n_times=120,
                coupling_law="fixed",
            ):
                A = weighted_adjacency(graph, pos, coupling_law=coupling_law)
                H_graph = build_hamiltonian(A, J=J, disorder_strength_over_J=disorder_strength_over_J, seed=seed)
                n = graph.number_of_nodes()
                sink = n
                loss = n + 1
                dim = n + 2

                H = np.zeros((dim, dim), dtype=complex)
                H[:n, :n] = H_graph

                jumps = []
                gamma_phi = gamma_phi_over_J * J
                if gamma_phi > 0:
                    for i in range(n):
                        jumps.append(jump(dim, i, i, gamma_phi))

                if sink_rate_over_J > 0:
                    jumps.append(jump(dim, sink, target_site, sink_rate_over_J * J))

                if loss_rate_over_J > 0:
                    for i in range(n):
                        jumps.append(jump(dim, loss, i, loss_rate_over_J * J))

                rho0 = np.zeros((dim, dim), dtype=complex)
                rho0[initial_site, initial_site] = 1.0
                rho0_vec = rho0.reshape(-1, order="F")

                L = liouvillian(H, jumps)
                times = np.linspace(0, t_final, n_times)
                vecs = expm_multiply(L, rho0_vec, start=0.0, stop=t_final, num=n_times)
                pos_array = np.vstack([pos[i] for i in range(n)])

                rows = []
                node_populations = []
                for t, vec in zip(times, vecs):
                    rho = vec.reshape((dim, dim), order="F")
                    rho = 0.5 * (rho + rho.conj().T)
                    obs = graph_observables(rho, n, pos_array)
                    node_populations.append(obs["node_populations"])
                    rows.append({
                        "time": float(t),
                        "target_arrival": float(np.real(rho[sink, sink])),
                        "loss": float(np.real(rho[loss, loss])),
                        "graph_population": obs["graph_population"],
                        "von_neumann_entropy": obs["von_neumann_entropy"],
                        "purity": obs["purity"],
                        "coherence_l1": obs["coherence_l1"],
                        "population_shannon_entropy": obs["population_shannon_entropy"],
                        "participation_ratio": obs["participation_ratio"],
                        "ipr": obs["ipr"],
                        "msd": obs["msd"],
                        "trace_error": abs(float(np.real(np.trace(rho))) - 1.0),
                    })

                return pd.DataFrame(rows), np.asarray(node_populations)
            """
        ),
    ]


def _experiment_cells() -> list[dict[str, object]]:
    return [
        _markdown("## 4. First experiment: one excitation on one chain"),
        _code(
            r"""
            graph, pos = make_graph("chain", n=6, seed=3)
            initial_site = 0
            target_site = 5
            draw_graph(graph, pos, initial_site=initial_site, target_site=target_site, title="Chain: initial site 0, target site 5")

            result, node_pop = simulate_open_quantum_transport(
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

            fig, axes = plt.subplots(1, 3, figsize=(16, 4.2))
            axes[0].plot(result["time"], node_pop)
            axes[0].set_title("Population on graph sites")
            axes[0].set_xlabel("time")
            axes[0].set_ylabel("population")

            axes[1].plot(result["time"], result["target_arrival"], label="target arrival", color="#d62728")
            axes[1].plot(result["time"], result["loss"], label="loss", color="#555555")
            axes[1].plot(result["time"], result["graph_population"], label="still in graph", color="#1f77b4")
            axes[1].set_title("Population closure")
            axes[1].set_xlabel("time")
            axes[1].set_ylabel("probability")
            axes[1].legend()

            axes[2].plot(result["time"], result["von_neumann_entropy"], label="von Neumann entropy", color="#2ca02c")
            axes[2].plot(result["time"], result["purity"], label="purity", color="#9467bd")
            axes[2].set_title("Mixing diagnostics")
            axes[2].set_xlabel("time")
            axes[2].legend()
            plt.tight_layout()
            plt.show()

            result.tail(1)[[
                "target_arrival",
                "loss",
                "graph_population",
                "von_neumann_entropy",
                "purity",
                "coherence_l1",
                "participation_ratio",
                "trace_error",
            ]]
            """
        ),
        _markdown(
            r"""
            ## 5. Scan phase scrambling

            We now change only `gamma_phi/J`, the phase-scrambling rate compared with the coherent coupling strength. The relevant question is whether nonzero phase scrambling improves target arrival, not whether entropy simply increases.
            """
        ),
        _code(
            r"""
            def choose_target(graph, pos, initial_site, target_style="far"):
                distances = nx.single_source_shortest_path_length(graph, initial_site)
                candidates = [node for node in graph.nodes if node != initial_site]
                if target_style == "near":
                    return min(candidates, key=lambda node: (distances.get(node, 999), node))
                if target_style == "far":
                    return max(candidates, key=lambda node: (distances.get(node, -1), -node))
                centrality = nx.closeness_centrality(graph)
                if target_style == "high_centrality":
                    return max(candidates, key=lambda node: centrality[node])
                if target_style == "low_centrality":
                    return min(candidates, key=lambda node: centrality[node])
                raise ValueError(f"Unknown target style: {target_style}")


            def dephasing_scan(family, n=8, target_style="far", W=0.6, seed=3, gamma_values=None):
                if gamma_values is None:
                    gamma_values = [0.0, 0.03, 0.05, 0.1, 0.2, 0.4, 0.8, 1.2]
                graph, pos = make_graph(family, n=n, seed=seed)
                initial_site = min(graph.nodes, key=lambda i: (pos[i][0] + pos[i][1], i))
                target_site = choose_target(graph, pos, initial_site, target_style=target_style)

                rows = []
                for gamma in gamma_values:
                    out, _ = simulate_open_quantum_transport(
                        graph,
                        pos,
                        initial_site=initial_site,
                        target_site=target_site,
                        disorder_strength_over_J=W,
                        gamma_phi_over_J=gamma,
                        seed=seed,
                        t_final=12,
                        n_times=100,
                    )
                    final = out.iloc[-1].to_dict()
                    final.update({
                        "family": family,
                        "n": graph.number_of_nodes(),
                        "seed": seed,
                        "W_over_J": W,
                        "gamma_phi_over_J": gamma,
                        "initial_site": initial_site,
                        "target_site": target_site,
                        "target_style": target_style,
                    })
                    rows.append(final)

                df = pd.DataFrame(rows)
                zero = float(df.loc[df["gamma_phi_over_J"] == 0.0, "target_arrival"].iloc[0])
                df["gain_over_zero_dephasing"] = df["target_arrival"] - zero
                return df, graph, pos, initial_site, target_site


            scan = pd.concat(
                [dephasing_scan(family, n=8, W=0.6, seed=3)[0] for family in ["chain", "ring", "complete", "star"]],
                ignore_index=True,
            )

            fig, axes = plt.subplots(1, 2, figsize=(14, 4.4))
            for family, group in scan.groupby("family"):
                axes[0].plot(group["gamma_phi_over_J"], group["target_arrival"], marker="o", label=family)
                axes[1].plot(group["gamma_phi_over_J"], group["von_neumann_entropy"], marker="o", label=family)
            axes[0].set_title("Target arrival versus phase scrambling")
            axes[0].set_xlabel("gamma_phi/J")
            axes[0].set_ylabel("target arrival")
            axes[0].legend()
            axes[1].set_title("Final graph-normalized von Neumann entropy")
            axes[1].set_xlabel("gamma_phi/J")
            axes[1].set_ylabel("entropy in nats")
            axes[1].legend()
            plt.tight_layout()
            plt.show()

            scan.groupby("family")[["target_arrival", "gain_over_zero_dephasing", "von_neumann_entropy", "purity"]].max().round(4)
            """
        ),
        _markdown(
            r"""
            ## 6. Classical control

            A classical control prevents us from calling a result quantum when it is only a graph-connectivity effect. The code below uses a continuous-time rate equation on the same graph, same initial site, same target site, same loss, and same final time.
            """
        ),
        _code(
            r"""
            def simulate_classical_transport(graph, initial_site, target_site, hopping_rate=1.0, sink_rate=0.65, loss_rate=0.02, t_final=12.0, n_times=120):
                n = graph.number_of_nodes()
                sink = n
                loss = n + 1
                dim = n + 2
                K = np.zeros((dim, dim), dtype=float)

                for i, j in graph.edges:
                    K[j, i] += hopping_rate
                    K[i, i] -= hopping_rate
                    K[i, j] += hopping_rate
                    K[j, j] -= hopping_rate

                K[sink, target_site] += sink_rate
                K[target_site, target_site] -= sink_rate
                for i in range(n):
                    K[loss, i] += loss_rate
                    K[i, i] -= loss_rate

                p0 = np.zeros(dim)
                p0[initial_site] = 1.0
                times = np.linspace(0, t_final, n_times)
                traj = expm_multiply(K, p0, start=0.0, stop=t_final, num=n_times)
                return pd.DataFrame({
                    "time": times,
                    "target_arrival_classical": traj[:, sink],
                    "loss_classical": traj[:, loss],
                    "graph_population_classical": traj[:, :n].sum(axis=1),
                })


            graph, pos = make_graph("ring", n=8, seed=3)
            initial_site = 4
            target_site = 0
            quantum, _ = simulate_open_quantum_transport(graph, pos, initial_site, target_site, disorder_strength_over_J=0.6, gamma_phi_over_J=0.1, seed=3, t_final=12, n_times=140)
            classical = simulate_classical_transport(graph, initial_site, target_site, t_final=12, n_times=140)

            plt.figure(figsize=(8, 4.6))
            plt.plot(quantum["time"], quantum["target_arrival"], label="open quantum model", color="#1f77b4")
            plt.plot(classical["time"], classical["target_arrival_classical"], label="classical rate model", color="#ff7f0e")
            plt.title("Same graph, same target, same final time")
            plt.xlabel("time")
            plt.ylabel("target arrival")
            plt.legend()
            plt.show()

            pd.DataFrame([{
                "family": "ring",
                "initial_site": initial_site,
                "target_site": target_site,
                "quantum_arrival": float(quantum["target_arrival"].iloc[-1]),
                "classical_arrival": float(classical["target_arrival_classical"].iloc[-1]),
                "quantum_minus_classical": float(quantum["target_arrival"].iloc[-1] - classical["target_arrival_classical"].iloc[-1]),
            }])
            """
        ),
        _markdown("## 7. Graph gallery"),
        _code(
            r"""
            gallery_families = [
                "chain", "ring", "star", "complete",
                "bottleneck", "clustered", "modular_two_community", "random_geometric",
                "square_lattice_2d", "erdos_renyi", "watts_strogatz_small_world", "barabasi_albert_scale_free",
                "sierpinski_gasket", "sierpinski_carpet_like",
            ]

            ncols = 4
            nrows = math.ceil(len(gallery_families) / ncols)
            fig, axes = plt.subplots(nrows, ncols, figsize=(15, 3.2 * nrows))
            for ax, family in zip(axes.flat, gallery_families):
                graph, pos = make_graph(family, n=10, seed=11)
                initial_site = min(graph.nodes)
                target_site = max(graph.nodes)
                colors = ["#1f77b4" if node == initial_site else "#d62728" if node == target_site else "#d9d9d9" for node in graph.nodes]
                nx.draw_networkx_edges(graph, pos, ax=ax, alpha=0.45, width=1.2)
                nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=colors, edgecolors="#222222", linewidths=0.5, node_size=150)
                ax.set_title(family, fontsize=10)
                ax.axis("equal")
                ax.axis("off")
            for ax in axes.flat[len(gallery_families):]:
                ax.axis("off")
            plt.suptitle("Graph families: blue = possible initial node, red = possible target node", y=1.01)
            plt.tight_layout()
            plt.show()
            """
        ),
    ]


def _evidence_cells() -> list[dict[str, object]]:
    return [
        _markdown(
            r"""
            ## 8. Evidence-prep campaign summary

            This is the non-smoke local campaign already produced by the lab:

            `dynamic_network_atlas_evidence_prep`

            It has 1032 records across 7 graph families, sizes 8 and 12, quantum simulations, matching classical controls, confidence intervals, and numerical validation.
            """
        ),
        _code(
            r"""
            evidence = pd.DataFrame([
                {"family": "bottleneck", "records": 96, "arrival": 0.46699, "arrival_ci_low": 0.44699, "arrival_ci_high": 0.48699, "dephasing_gain": 0.06949, "gain_ci_low": 0.05459, "gain_ci_high": 0.08438, "quantum_minus_classical": 0.15300, "qmc_ci_low": 0.10078, "qmc_ci_high": 0.20521, "von_neumann_entropy": 1.27134, "purity": 0.49895, "participation_ratio": 7.44193, "verdict": "quantum_higher"},
                {"family": "chain", "records": 96, "arrival": 0.50599, "arrival_ci_low": 0.47651, "arrival_ci_high": 0.53547, "dephasing_gain": 0.07650, "gain_ci_low": 0.05790, "gain_ci_high": 0.09509, "quantum_minus_classical": 0.12373, "qmc_ci_low": 0.06705, "qmc_ci_high": 0.18040, "von_neumann_entropy": 1.18734, "purity": 0.52730, "participation_ratio": 7.38187, "verdict": "quantum_higher"},
                {"family": "clustered", "records": 96, "arrival": 0.46581, "arrival_ci_low": 0.44595, "arrival_ci_high": 0.48567, "dephasing_gain": 0.06182, "gain_ci_low": 0.04732, "gain_ci_high": 0.07632, "quantum_minus_classical": 0.17541, "qmc_ci_low": 0.12798, "qmc_ci_high": 0.22284, "von_neumann_entropy": 1.11908, "purity": 0.55626, "participation_ratio": 7.09557, "verdict": "quantum_higher"},
                {"family": "modular_two_community", "records": 288, "arrival": 0.35980, "arrival_ci_low": 0.34251, "arrival_ci_high": 0.37709, "dephasing_gain": 0.09017, "gain_ci_low": 0.08182, "gain_ci_high": 0.09853, "quantum_minus_classical": 0.04759, "qmc_ci_low": 0.03565, "qmc_ci_high": 0.05954, "von_neumann_entropy": 1.79710, "purity": 0.27869, "participation_ratio": 8.55639, "verdict": "classical_explains"},
                {"family": "random_geometric", "records": 264, "arrival": 0.34013, "arrival_ci_low": 0.32394, "arrival_ci_high": 0.35633, "dephasing_gain": 0.08879, "gain_ci_low": 0.08084, "gain_ci_high": 0.09674, "quantum_minus_classical": 0.05580, "qmc_ci_low": 0.03892, "qmc_ci_high": 0.07269, "von_neumann_entropy": 1.83822, "purity": 0.27553, "participation_ratio": 8.79456, "verdict": "quantum_higher"},
                {"family": "ring", "records": 96, "arrival": 0.45941, "arrival_ci_low": 0.43752, "arrival_ci_high": 0.48131, "dephasing_gain": 0.04608, "gain_ci_low": 0.03442, "gain_ci_high": 0.05774, "quantum_minus_classical": 0.14537, "qmc_ci_low": 0.10755, "qmc_ci_high": 0.18319, "von_neumann_entropy": 1.18050, "purity": 0.53124, "participation_ratio": 7.50821, "verdict": "quantum_higher"},
                {"family": "square_lattice_2d", "records": 96, "arrival": 0.44555, "arrival_ci_low": 0.43338, "arrival_ci_high": 0.45771, "dephasing_gain": 0.07487, "gain_ci_low": 0.05847, "gain_ci_high": 0.09127, "quantum_minus_classical": 0.09143, "qmc_ci_low": 0.04977, "qmc_ci_high": 0.13308, "von_neumann_entropy": 1.49106, "purity": 0.39649, "participation_ratio": 8.17199, "verdict": "quantum_higher"},
            ])

            evidence.sort_values("arrival", ascending=False)
            """
        ),
        _code(
            r"""
            fig, axes = plt.subplots(2, 2, figsize=(15, 9))

            ordered = evidence.sort_values("arrival", ascending=True)
            y = np.arange(len(ordered))
            axes[0, 0].barh(y, ordered["arrival"], xerr=[ordered["arrival"] - ordered["arrival_ci_low"], ordered["arrival_ci_high"] - ordered["arrival"]], color="#4c78a8", alpha=0.85)
            axes[0, 0].set_yticks(y, ordered["family"])
            axes[0, 0].set_title("Target arrival with 95% confidence intervals")
            axes[0, 0].set_xlabel("arrival")

            ordered_gain = evidence.sort_values("dephasing_gain", ascending=True)
            y = np.arange(len(ordered_gain))
            axes[0, 1].barh(y, ordered_gain["dephasing_gain"], xerr=[ordered_gain["dephasing_gain"] - ordered_gain["gain_ci_low"], ordered_gain["gain_ci_high"] - ordered_gain["dephasing_gain"]], color="#f58518", alpha=0.85)
            axes[0, 1].axvline(0.05, color="black", linestyle="--", linewidth=1, label="clear-effect threshold")
            axes[0, 1].set_yticks(y, ordered_gain["family"])
            axes[0, 1].set_title("Gain from phase scrambling")
            axes[0, 1].set_xlabel("best arrival minus zero-dephasing arrival")
            axes[0, 1].legend()

            ordered_qmc = evidence.sort_values("quantum_minus_classical", ascending=True)
            y = np.arange(len(ordered_qmc))
            axes[1, 0].barh(y, ordered_qmc["quantum_minus_classical"], xerr=[ordered_qmc["quantum_minus_classical"] - ordered_qmc["qmc_ci_low"], ordered_qmc["qmc_ci_high"] - ordered_qmc["quantum_minus_classical"]], color="#54a24b", alpha=0.85)
            axes[1, 0].axvline(0.05, color="black", linestyle="--", linewidth=1, label="quantum-higher threshold")
            axes[1, 0].set_yticks(y, ordered_qmc["family"])
            axes[1, 0].set_title("Open quantum model minus classical control")
            axes[1, 0].set_xlabel("arrival difference")
            axes[1, 0].legend()

            scatter = axes[1, 1].scatter(evidence["von_neumann_entropy"], evidence["arrival"], s=120, c=evidence["dephasing_gain"], cmap="viridis", edgecolor="black")
            for _, row in evidence.iterrows():
                axes[1, 1].annotate(row["family"], (row["von_neumann_entropy"], row["arrival"]), fontsize=8, xytext=(5, 5), textcoords="offset points")
            axes[1, 1].set_title("Entropy is not the same as useful arrival")
            axes[1, 1].set_xlabel("final graph-normalized von Neumann entropy")
            axes[1, 1].set_ylabel("target arrival")
            cbar = plt.colorbar(scatter, ax=axes[1, 1])
            cbar.set_label("dephasing gain")
            plt.tight_layout()
            plt.show()
            """
        ),
        _markdown("## 9. Small reproducible campaign with seeds"),
        _code(
            r"""
            FAMILIES = ["chain", "ring", "random_geometric", "square_lattice_2d"]
            N_SITES = 8
            SEEDS = [3, 5]
            DISORDER_VALUES = [0.0, 0.6, 1.2]
            GAMMA_VALUES = [0.0, 0.1, 0.4, 0.8]

            campaign_rows = []
            for family in FAMILIES:
                for seed in SEEDS:
                    for W in DISORDER_VALUES:
                        scan_df, graph, pos, initial_site, target_site = dephasing_scan(
                            family,
                            n=N_SITES,
                            target_style="far",
                            W=W,
                            seed=seed,
                            gamma_values=GAMMA_VALUES,
                        )
                        best = scan_df.loc[scan_df["target_arrival"].idxmax()].to_dict()
                        classical = simulate_classical_transport(graph, initial_site, target_site, t_final=12, n_times=100)
                        best["classical_arrival"] = float(classical["target_arrival_classical"].iloc[-1])
                        best["quantum_minus_classical"] = best["target_arrival"] - best["classical_arrival"]
                        campaign_rows.append(best)

            mini = pd.DataFrame(campaign_rows)
            summary = mini.groupby("family").agg(
                arrival_mean=("target_arrival", "mean"),
                arrival_std=("target_arrival", "std"),
                gain_mean=("gain_over_zero_dephasing", "mean"),
                entropy_mean=("von_neumann_entropy", "mean"),
                purity_mean=("purity", "mean"),
                q_minus_classical_mean=("quantum_minus_classical", "mean"),
            ).reset_index()
            summary.round(4)
            """
        ),
        _code(
            r"""
            fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
            axes[0].bar(summary["family"], summary["arrival_mean"], color="#4c78a8")
            axes[0].set_title("Mean target arrival")
            axes[0].tick_params(axis="x", rotation=30)

            axes[1].bar(summary["family"], summary["entropy_mean"], color="#72b7b2")
            axes[1].set_title("Mean final von Neumann entropy")
            axes[1].tick_params(axis="x", rotation=30)

            axes[2].bar(summary["family"], summary["q_minus_classical_mean"], color="#54a24b")
            axes[2].axhline(0.05, color="black", linestyle="--", linewidth=1)
            axes[2].set_title("Quantum minus classical arrival")
            axes[2].tick_params(axis="x", rotation=30)
            plt.tight_layout()
            plt.show()
            """
        ),
    ]


def _closing_cells() -> list[dict[str, object]]:
    return [
        _markdown(
            r"""
            ## 10. Conservative scientific reading

            The useful part is not the existence of many plots. The useful part is the controlled comparison:

            1. Same graph, same initial site, same target site, same time, same loss.
            2. Change one physical knob at a time.
            3. Measure target arrival, von Neumann entropy, coherence, purity, participation, and classical control.
            4. Add seeds and confidence intervals before claiming a physical effect.

            Current conservative claim:

            **Finite graph families leave measurable dynamic fingerprints in open quantum transport, and target arrival cannot be replaced by entropy or spreading alone.**

            Presentation version:

            - We simulate an effective open quantum network, not quantum hardware.
            - Nodes are local quantum sites; edges are coherent couplings; the target channel records useful arrival.
            - Von Neumann entropy measures state mixing inside the graph.
            - More entropy does not automatically mean better transport.
            - Every quantum claim needs a classical control and uncertainty.
            """
        ),
    ]


def build_notebook() -> dict[str, object]:
    cells: list[dict[str, object]] = []
    cells.extend(_intro_cells())
    cells.extend(_graph_cells())
    cells.extend(_simulation_cells())
    cells.extend(_experiment_cells())
    cells.extend(_evidence_cells())
    cells.extend(_closing_cells())
    return {
        "cells": cells,
        "metadata": {
            "colab": {"provenance": [], "include_colab_link": True},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.x"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build() -> dict[str, str]:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(
        json.dumps(build_notebook(), indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"notebook": str(NOTEBOOK_PATH), "colab_link": COLAB_GITHUB_LINK}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
