from __future__ import annotations

import math

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.linalg import expm_multiply


GRAPH_FAMILIES = (
    "chain",
    "ring",
    "complete",
    "star",
    "square_lattice_2d",
    "bottleneck",
    "clustered",
    "modular_two_community",
    "random_geometric",
    "erdos_renyi",
    "watts_strogatz_small_world",
    "barabasi_albert_scale_free",
    "sierpinski_gasket",
    "sierpinski_carpet_like",
)


def _circle_positions(n: int, radius: float = 1.0) -> dict[int, np.ndarray]:
    return {
        i: np.array(
            [
                radius * math.cos(2.0 * math.pi * i / n),
                radius * math.sin(2.0 * math.pi * i / n),
            ],
            dtype=float,
        )
        for i in range(n)
    }


def _relabel(graph: nx.Graph, pos: dict[object, np.ndarray]) -> tuple[nx.Graph, dict[int, np.ndarray]]:
    mapping = {node: k for k, node in enumerate(graph.nodes())}
    graph = nx.relabel_nodes(graph, mapping)
    relabeled = {mapping[node]: np.asarray(value, dtype=float) for node, value in pos.items()}
    return graph, relabeled


def make_graph(family: str = "chain", n: int = 8, seed: int = 3) -> tuple[nx.Graph, dict[int, np.ndarray]]:
    rng = np.random.default_rng(seed)

    if family == "chain":
        graph = nx.path_graph(n)
        pos = {i: np.array([i, 0.0], dtype=float) for i in range(n)}
    elif family == "ring":
        graph = nx.cycle_graph(n)
        pos = _circle_positions(n)
    elif family == "complete":
        graph = nx.complete_graph(n)
        pos = _circle_positions(n)
    elif family == "star":
        graph = nx.star_graph(n - 1)
        pos = {0: np.array([0.0, 0.0], dtype=float)}
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
            for a, b in zip(group[:-1], group[1:], strict=False):
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
            angle = 2.0 * math.pi * k / max(1, len(left))
            pos[node] = np.array([math.cos(angle), math.sin(angle)], dtype=float)
        for k, node in enumerate(right):
            angle = 2.0 * math.pi * k / max(1, len(right))
            pos[node] = np.array([3.0 + math.cos(angle), math.sin(angle)], dtype=float)
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
        for prob in (0.35, 0.45, 0.55, 0.70):
            graph = nx.erdos_renyi_graph(n, prob, seed=seed)
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
        coords = {
            0: (0.0, 0.0),
            1: (1.0, 0.0),
            2: (2.0, 0.0),
            3: (0.5, 0.9),
            4: (1.5, 0.9),
            5: (1.0, 1.8),
        }
        graph = nx.Graph()
        graph.add_nodes_from(coords)
        graph.add_edges_from([(0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4), (3, 4), (3, 5), (4, 5)])
        pos = {i: np.array(value, dtype=float) for i, value in coords.items()}
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
        raise ValueError(f"Unsupported family: {family}")

    graph, pos = _relabel(graph, pos)
    return graph, pos


def draw_graph(
    graph: nx.Graph,
    pos: dict[int, np.ndarray],
    *,
    initial_site: int | None = None,
    target_site: int | None = None,
    title: str = "",
    ax=None,
) -> None:
    if ax is None:
        _, ax = plt.subplots(figsize=(5.2, 4.2))
    colors = []
    for node in graph.nodes():
        if node == initial_site:
            colors.append("#1f77b4")
        elif node == target_site:
            colors.append("#d62728")
        else:
            colors.append("#d9d9d9")
    nx.draw_networkx_edges(graph, pos, ax=ax, alpha=0.45, width=1.6)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=colors, edgecolors="#222222", linewidths=0.7, node_size=260)
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=9)
    ax.set_title(title)
    ax.axis("equal")
    ax.axis("off")


def weighted_adjacency(
    graph: nx.Graph,
    pos: dict[int, np.ndarray],
    *,
    coupling_law: str = "fixed",
    length_scale: float = 1.0,
) -> np.ndarray:
    n = graph.number_of_nodes()
    adjacency = np.zeros((n, n), dtype=float)
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
        adjacency[i, j] = adjacency[j, i] = weight
    return adjacency


def build_hamiltonian(adjacency: np.ndarray, *, J: float = 1.0, disorder_strength_over_J: float = 0.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = adjacency.shape[0]
    onsite = disorder_strength_over_J * J * rng.uniform(-0.5, 0.5, size=n)
    hamiltonian = J * adjacency.astype(complex)
    hamiltonian += np.diag(onsite.astype(complex))
    return hamiltonian


def _jump(dim: int, row: int, col: int, rate: float) -> np.ndarray:
    operator = np.zeros((dim, dim), dtype=complex)
    operator[row, col] = math.sqrt(rate)
    return operator


def _liouvillian(hamiltonian: np.ndarray, jumps: list[np.ndarray]) -> np.ndarray:
    dim = hamiltonian.shape[0]
    identity = np.eye(dim, dtype=complex)
    superoperator = -1j * (np.kron(identity, hamiltonian) - np.kron(hamiltonian.T, identity))
    for operator in jumps:
        cd_c = operator.conj().T @ operator
        superoperator += np.kron(operator.conj(), operator)
        superoperator += -0.5 * np.kron(identity, cd_c)
        superoperator += -0.5 * np.kron(cd_c.T, identity)
    return superoperator


def von_neumann_entropy(rho: np.ndarray, eps: float = 1e-12) -> float:
    rho = 0.5 * (rho + rho.conj().T)
    values = np.linalg.eigvalsh(rho).real
    values = values[values > eps]
    return float(-np.sum(values * np.log(values))) if values.size else 0.0


def _shannon_entropy(probabilities: np.ndarray, eps: float = 1e-12) -> float:
    total = float(np.sum(probabilities))
    if total <= eps:
        return 0.0
    normalized = np.asarray(probabilities, dtype=float) / total
    normalized = normalized[normalized > eps]
    return float(-np.sum(normalized * np.log(normalized)))


def _graph_observables(rho: np.ndarray, n_graph: int, pos_array: np.ndarray) -> dict[str, float | np.ndarray]:
    graph_block = rho[:n_graph, :n_graph]
    node_populations = np.maximum(np.real(np.diag(graph_block)), 0.0)
    graph_population = float(node_populations.sum())
    if graph_population > 1e-12:
        rho_g = graph_block / graph_population
        p_g = node_populations / graph_population
    else:
        rho_g = graph_block
        p_g = np.zeros(n_graph)

    offdiag = rho_g - np.diag(np.diag(rho_g))
    mean_position = p_g @ pos_array if p_g.sum() > 0 else np.zeros(2)
    msd = float(np.sum(p_g * np.sum((pos_array - mean_position) ** 2, axis=1))) if p_g.sum() > 0 else 0.0
    ipr = float(np.sum(p_g**2))
    return {
        "node_populations": node_populations,
        "graph_population": graph_population,
        "von_neumann_entropy": von_neumann_entropy(rho_g),
        "purity": float(np.real(np.trace(rho_g @ rho_g))),
        "coherence_l1": float(np.sum(np.abs(offdiag))),
        "population_shannon_entropy": _shannon_entropy(p_g),
        "participation_ratio": float(1.0 / ipr) if ipr > 1e-12 else 0.0,
        "ipr": ipr,
        "msd": msd,
    }


def simulate_open_quantum_transport(
    graph: nx.Graph,
    pos: dict[int, np.ndarray],
    *,
    initial_site: int,
    target_site: int,
    disorder_strength_over_J: float = 0.0,
    gamma_phi_over_J: float = 0.1,
    seed: int = 0,
    J: float = 1.0,
    sink_rate_over_J: float = 0.65,
    loss_rate_over_J: float = 0.02,
    t_final: float = 12.0,
    n_times: int = 120,
    coupling_law: str = "fixed",
) -> tuple[pd.DataFrame, np.ndarray]:
    adjacency = weighted_adjacency(graph, pos, coupling_law=coupling_law)
    graph_hamiltonian = build_hamiltonian(adjacency, J=J, disorder_strength_over_J=disorder_strength_over_J, seed=seed)
    n = graph.number_of_nodes()
    sink = n
    loss = n + 1
    dim = n + 2

    hamiltonian = np.zeros((dim, dim), dtype=complex)
    hamiltonian[:n, :n] = graph_hamiltonian

    jumps: list[np.ndarray] = []
    gamma_phi = gamma_phi_over_J * J
    if gamma_phi > 0:
        for i in range(n):
            jumps.append(_jump(dim, i, i, gamma_phi))
    if sink_rate_over_J > 0:
        jumps.append(_jump(dim, sink, target_site, sink_rate_over_J * J))
    if loss_rate_over_J > 0:
        for i in range(n):
            jumps.append(_jump(dim, loss, i, loss_rate_over_J * J))

    rho0 = np.zeros((dim, dim), dtype=complex)
    rho0[initial_site, initial_site] = 1.0
    rho0_vec = rho0.reshape(-1, order="F")

    times = np.linspace(0.0, t_final, n_times)
    trajectories = expm_multiply(_liouvillian(hamiltonian, jumps), rho0_vec, start=0.0, stop=t_final, num=n_times)
    pos_array = np.vstack([pos[i] for i in range(n)])

    rows: list[dict[str, float]] = []
    node_rows: list[np.ndarray] = []
    for time_value, vec in zip(times, trajectories, strict=False):
        rho = vec.reshape((dim, dim), order="F")
        rho = 0.5 * (rho + rho.conj().T)
        obs = _graph_observables(rho, n, pos_array)
        node_rows.append(obs["node_populations"])
        rows.append(
            {
                "time": float(time_value),
                "target_arrival": float(np.real(rho[sink, sink])),
                "loss": float(np.real(rho[loss, loss])),
                "graph_population": float(obs["graph_population"]),
                "von_neumann_entropy": float(obs["von_neumann_entropy"]),
                "purity": float(obs["purity"]),
                "coherence_l1": float(obs["coherence_l1"]),
                "population_shannon_entropy": float(obs["population_shannon_entropy"]),
                "participation_ratio": float(obs["participation_ratio"]),
                "ipr": float(obs["ipr"]),
                "msd": float(obs["msd"]),
                "trace_error": abs(float(np.real(np.trace(rho))) - 1.0),
            }
        )
    return pd.DataFrame(rows), np.asarray(node_rows)


def simulate_classical_transport(
    graph: nx.Graph,
    *,
    initial_site: int,
    target_site: int,
    hopping_rate: float = 1.0,
    sink_rate: float = 0.65,
    loss_rate: float = 0.02,
    t_final: float = 12.0,
    n_times: int = 120,
) -> pd.DataFrame:
    n = graph.number_of_nodes()
    sink = n
    loss = n + 1
    dim = n + 2
    generator = np.zeros((dim, dim), dtype=float)

    for i, j in graph.edges:
        generator[j, i] += hopping_rate
        generator[i, i] -= hopping_rate
        generator[i, j] += hopping_rate
        generator[j, j] -= hopping_rate

    generator[sink, target_site] += sink_rate
    generator[target_site, target_site] -= sink_rate
    for i in range(n):
        generator[loss, i] += loss_rate
        generator[i, i] -= loss_rate

    p0 = np.zeros(dim, dtype=float)
    p0[initial_site] = 1.0
    times = np.linspace(0.0, t_final, n_times)
    trajectory = expm_multiply(generator, p0, start=0.0, stop=t_final, num=n_times)
    return pd.DataFrame(
        {
            "time": times,
            "target_arrival_classical": trajectory[:, sink],
            "loss_classical": trajectory[:, loss],
            "graph_population_classical": trajectory[:, :n].sum(axis=1),
        }
    )
