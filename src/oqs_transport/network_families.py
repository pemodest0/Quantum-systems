from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from .mediums import bottleneck_lattice_coordinates, chain_coordinates, clustered_lattice_coordinates, ring_coordinates, square_lattice_coordinates
from .networks import chain_adjacency, complete_adjacency, ring_adjacency


SUPPORTED_DYNAMIC_NETWORK_FAMILIES = (
    "chain",
    "ring",
    "complete",
    "star",
    "erdos_renyi",
    "watts_strogatz_small_world",
    "barabasi_albert_scale_free",
    "modular_two_community",
    "random_geometric",
    "square_lattice_2d",
    "bottleneck",
    "clustered",
    "sierpinski_gasket",
    "sierpinski_carpet_like",
)


@dataclass(frozen=True)
class NetworkInstance:
    family: str
    instance_id: str
    adjacency: np.ndarray
    coordinates: np.ndarray
    labels: tuple[str, ...]
    seed: int
    metadata: dict[str, float | int | str]


def _as_adjacency(graph: nx.Graph, n_sites: int) -> np.ndarray:
    adjacency = nx.to_numpy_array(graph, nodelist=list(range(n_sites)), dtype=float)
    adjacency = np.maximum(adjacency, adjacency.T)
    np.fill_diagonal(adjacency, 0.0)
    return adjacency


def _ensure_connected(graph: nx.Graph, rng: np.random.Generator) -> nx.Graph:
    graph = graph.copy()
    components = [list(component) for component in nx.connected_components(graph)]
    if len(components) <= 1:
        return graph
    for left, right in zip(components[:-1], components[1:], strict=False):
        graph.add_edge(int(rng.choice(left)), int(rng.choice(right)))
    return graph


def _spring_coordinates(graph: nx.Graph, seed: int) -> np.ndarray:
    positions = nx.spring_layout(graph, seed=int(seed), dim=2)
    return np.asarray([positions[node] for node in range(graph.number_of_nodes())], dtype=float)


def _circle_coordinates(n_sites: int) -> np.ndarray:
    angles = np.linspace(0.0, 2.0 * np.pi, int(n_sites), endpoint=False)
    return np.column_stack([np.cos(angles), np.sin(angles)])


def star_adjacency(n_sites: int) -> np.ndarray:
    if n_sites < 3:
        raise ValueError("star requires at least 3 sites")
    adjacency = np.zeros((n_sites, n_sites), dtype=float)
    adjacency[0, 1:] = 1.0
    adjacency[1:, 0] = 1.0
    return adjacency


def _sierpinski_gasket_points(order: int) -> list[tuple[int, int]]:
    points = {(0, 0), (1, 0), (0, 1)}
    for _ in range(max(0, int(order))):
        scale = 2 ** (_ + 1)
        points = (
            {(x, y) for x, y in points}
            | {(x + scale, y) for x, y in points}
            | {(x, y + scale) for x, y in points}
        )
    return sorted(points, key=lambda point: (point[0] + point[1], point[0], point[1]))


def _sierpinski_carpet_points(order: int) -> list[tuple[int, int]]:
    points = [(0, 0)]
    for _ in range(max(1, int(order))):
        next_points: list[tuple[int, int]] = []
        for x, y in points:
            for dx in range(3):
                for dy in range(3):
                    if dx == 1 and dy == 1:
                        continue
                    next_points.append((3 * x + dx, 3 * y + dy))
        points = next_points
    return sorted(set(points), key=lambda point: (point[0] + point[1], point[0], point[1]))


def _fractal_graph_from_points(points: list[tuple[int, int]], n_sites: int) -> tuple[nx.Graph, np.ndarray]:
    selected = list(points[: int(n_sites)])
    if len(selected) < int(n_sites):
        raise ValueError("not enough fractal points for requested n_sites")
    index_by_point = {point: index for index, point in enumerate(selected)}
    graph = nx.Graph()
    graph.add_nodes_from(range(len(selected)))
    for index, (x, y) in enumerate(selected):
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            other = index_by_point.get(neighbor)
            if other is not None:
                graph.add_edge(index, other)
    coordinates = np.asarray(selected, dtype=float)
    coordinates -= np.mean(coordinates, axis=0, keepdims=True)
    scale = float(np.max(np.ptp(coordinates, axis=0)))
    if scale > 1e-12:
        coordinates /= scale
    return graph, coordinates


def generate_network_instance(
    family: str,
    *,
    n_sites: int,
    seed: int = 0,
    realization_index: int = 0,
) -> NetworkInstance:
    if family not in SUPPORTED_DYNAMIC_NETWORK_FAMILIES:
        raise ValueError(f"unsupported network family: {family}")
    if n_sites < 3:
        raise ValueError("n_sites must be at least 3")

    rng = np.random.default_rng(seed)
    labels = tuple(str(index) for index in range(n_sites))
    metadata: dict[str, float | int | str] = {"n_sites": int(n_sites), "realization_index": int(realization_index)}

    if family == "chain":
        adjacency = chain_adjacency(n_sites)
        coordinates = chain_coordinates(n_sites)
    elif family == "ring":
        adjacency = ring_adjacency(n_sites)
        coordinates = ring_coordinates(n_sites)
    elif family == "complete":
        adjacency = complete_adjacency(n_sites)
        coordinates = _circle_coordinates(n_sites)
    elif family == "star":
        adjacency = star_adjacency(n_sites)
        coordinates = _circle_coordinates(n_sites)
        coordinates[0] = np.array([0.0, 0.0])
    elif family == "erdos_renyi":
        probability = min(0.75, max(0.25, 2.5 / max(n_sites - 1, 1)))
        graph = nx.gnp_random_graph(n_sites, probability, seed=int(seed))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        coordinates = _spring_coordinates(graph, seed)
        metadata["edge_probability"] = float(probability)
    elif family == "watts_strogatz_small_world":
        k_neighbors = max(2, min(n_sites - 1, 4))
        if k_neighbors % 2 == 1:
            k_neighbors -= 1
        graph = nx.watts_strogatz_graph(n_sites, k_neighbors, 0.25, seed=int(seed))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        coordinates = _spring_coordinates(graph, seed)
        metadata["k_neighbors"] = int(k_neighbors)
        metadata["rewire_probability"] = 0.25
    elif family == "barabasi_albert_scale_free":
        attach_edges = max(1, min(3, n_sites // 4))
        graph = nx.barabasi_albert_graph(n_sites, attach_edges, seed=int(seed))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        coordinates = _spring_coordinates(graph, seed)
        metadata["attach_edges"] = int(attach_edges)
    elif family == "modular_two_community":
        sizes = [n_sites // 2, n_sites - n_sites // 2]
        probabilities = [[0.70, 0.08], [0.08, 0.70]]
        graph = nx.stochastic_block_model(sizes, probabilities, seed=int(seed))
        graph = nx.convert_node_labels_to_integers(graph)
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        coordinates = _spring_coordinates(graph, seed)
        metadata["p_in"] = 0.70
        metadata["p_out"] = 0.08
    elif family == "random_geometric":
        radius = min(0.75, max(0.35, np.sqrt(2.2 / n_sites)))
        graph = nx.random_geometric_graph(n_sites, radius, seed=int(seed))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        positions = nx.get_node_attributes(graph, "pos")
        coordinates = np.asarray([positions[node] for node in range(n_sites)], dtype=float)
        metadata["radius"] = float(radius)
    elif family == "square_lattice_2d":
        side = int(np.ceil(np.sqrt(n_sites)))
        coordinates = square_lattice_coordinates(side, side)[:n_sites]
        graph = nx.random_geometric_graph(n_sites, 1.05, pos={i: tuple(coordinates[i]) for i in range(n_sites)})
        adjacency = _as_adjacency(graph, n_sites)
        metadata["side"] = int(side)
    elif family == "bottleneck":
        n_rows = 2 if n_sites < 12 else 3
        n_cols_left = max(2, n_sites // (2 * n_rows))
        n_cols_right = n_cols_left
        coordinates = bottleneck_lattice_coordinates(n_rows, n_cols_left, n_cols_right)
        if coordinates.shape[0] < n_sites:
            extra = n_sites - coordinates.shape[0]
            tail = coordinates[-1] + np.column_stack([np.arange(1, extra + 1), np.zeros(extra)])
            coordinates = np.vstack([coordinates, tail])
        coordinates = coordinates[:n_sites]
        graph = nx.random_geometric_graph(n_sites, 1.05, pos={i: tuple(coordinates[i]) for i in range(n_sites)})
        if n_sites >= 4:
            graph.add_edge(max(0, n_sites // 2 - 1), min(n_sites - 1, n_sites // 2))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        metadata["n_rows"] = int(n_rows)
    elif family == "clustered":
        cluster_size = max(2, n_sites // 4)
        coordinates = clustered_lattice_coordinates(cluster_size)
        if coordinates.shape[0] < n_sites:
            extra = n_sites - coordinates.shape[0]
            tail = coordinates[-1] + np.column_stack([np.arange(1, extra + 1), np.zeros(extra)])
            coordinates = np.vstack([coordinates, tail])
        coordinates = coordinates[:n_sites]
        graph = nx.random_geometric_graph(n_sites, 1.05, pos={i: tuple(coordinates[i]) for i in range(n_sites)})
        if n_sites >= 4:
            graph.add_edge(max(0, n_sites // 2 - 1), min(n_sites - 1, n_sites // 2))
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        metadata["cluster_size"] = int(cluster_size)
    elif family == "sierpinski_gasket":
        order = 1
        while len(_sierpinski_gasket_points(order)) < n_sites:
            order += 1
        graph, coordinates = _fractal_graph_from_points(_sierpinski_gasket_points(order), n_sites)
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        metadata["fractal_order"] = int(order)
        metadata["fractal_type"] = "sierpinski_gasket"
    elif family == "sierpinski_carpet_like":
        order = 1
        while len(_sierpinski_carpet_points(order)) < n_sites:
            order += 1
        graph, coordinates = _fractal_graph_from_points(_sierpinski_carpet_points(order), n_sites)
        graph = _ensure_connected(graph, rng)
        adjacency = _as_adjacency(graph, n_sites)
        metadata["fractal_order"] = int(order)
        metadata["fractal_type"] = "sierpinski_carpet_like"
    else:
        raise ValueError(f"unsupported network family: {family}")

    instance_id = f"{family}_N{n_sites}_r{realization_index}_s{seed}"
    return NetworkInstance(
        family=family,
        instance_id=instance_id,
        adjacency=np.asarray(adjacency, dtype=float),
        coordinates=np.asarray(coordinates, dtype=float),
        labels=labels,
        seed=int(seed),
        metadata=metadata,
    )


def graph_from_adjacency(adjacency: np.ndarray) -> nx.Graph:
    adjacency = np.asarray(adjacency, dtype=float)
    graph = nx.from_numpy_array(adjacency)
    graph.remove_edges_from(nx.selfloop_edges(graph))
    return graph


def target_candidates(instance: NetworkInstance, *, initial_site: int) -> dict[str, int]:
    graph = graph_from_adjacency(instance.adjacency)
    n_sites = graph.number_of_nodes()
    initial_site = int(initial_site)
    lengths = nx.single_source_shortest_path_length(graph, initial_site)
    candidates = [node for node in range(n_sites) if node != initial_site]
    near = min(candidates, key=lambda node: (lengths.get(node, n_sites + 1), node))
    far = max(candidates, key=lambda node: (lengths.get(node, -1), -node))
    closeness = nx.closeness_centrality(graph)
    high = max(candidates, key=lambda node: (closeness.get(node, 0.0), -node))
    low = min(candidates, key=lambda node: (closeness.get(node, 0.0), node))
    return {
        "near": int(near),
        "far": int(far),
        "high_centrality": int(high),
        "low_centrality": int(low),
    }


def topology_metrics(instance: NetworkInstance, *, initial_site: int, trap_site: int) -> dict[str, float]:
    adjacency = np.asarray(instance.adjacency, dtype=float)
    graph = graph_from_adjacency(adjacency)
    n_sites = graph.number_of_nodes()
    degrees = dict(graph.degree())
    degree_values = np.asarray([degrees[node] for node in range(n_sites)], dtype=float)
    betweenness = nx.betweenness_centrality(graph, normalized=True)
    closeness = nx.closeness_centrality(graph)
    try:
        distance = float(nx.shortest_path_length(graph, int(initial_site), int(trap_site)))
    except nx.NetworkXNoPath:
        distance = float(n_sites + 1)
    try:
        communities = list(nx.community.greedy_modularity_communities(graph))
        modularity = float(nx.community.modularity(graph, communities)) if len(communities) > 1 else 0.0
    except ZeroDivisionError:
        modularity = 0.0

    eigenvalues, eigenvectors = np.linalg.eigh(adjacency)
    sorted_abs = np.sort(np.abs(eigenvalues))[::-1]
    spectral_radius = float(sorted_abs[0]) if sorted_abs.size else 0.0
    spectral_gap = float(sorted_abs[0] - sorted_abs[1]) if sorted_abs.size > 1 else 0.0
    rounded = np.round(eigenvalues, decimals=6)
    degeneracy = int(sum(count - 1 for count in np.unique(rounded, return_counts=True)[1] if count > 1))
    mode_overlap = np.abs(eigenvectors[int(initial_site), :] * eigenvectors[int(trap_site), :])
    spectral_initial_target_overlap = float(np.sum(mode_overlap))
    target_mode_weight = float(np.sum(np.abs(eigenvectors[int(trap_site), :]) ** 4))

    return {
        "n_sites": float(n_sites),
        "n_edges": float(graph.number_of_edges()),
        "density": float(nx.density(graph)),
        "mean_degree": float(np.mean(degree_values)),
        "std_degree": float(np.std(degree_values)),
        "initial_degree": float(degrees.get(int(initial_site), 0)),
        "target_degree": float(degrees.get(int(trap_site), 0)),
        "target_betweenness": float(betweenness.get(int(trap_site), 0.0)),
        "target_closeness": float(closeness.get(int(trap_site), 0.0)),
        "initial_target_distance": distance,
        "modularity_approx": modularity,
        "spectral_radius": spectral_radius,
        "spectral_gap": spectral_gap,
        "spectral_degeneracy_approx": float(degeneracy),
        "spectral_initial_target_overlap": spectral_initial_target_overlap,
        "target_mode_weight_ipr": target_mode_weight,
    }
