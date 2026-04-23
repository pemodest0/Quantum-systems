from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "scenario"


def build_graph_from_adjacency(adjacency: np.ndarray) -> nx.Graph:
    adjacency = np.asarray(adjacency, dtype=float)
    n_sites = adjacency.shape[0]
    graph = nx.Graph()
    graph.add_nodes_from(range(n_sites))
    for i in range(n_sites):
        for j in range(i + 1, n_sites):
            if adjacency[i, j] != 0.0:
                graph.add_edge(i, j, weight=float(adjacency[i, j]))
    return graph


def graph_positions(graph: nx.Graph, topology: str, coordinates: np.ndarray | None = None) -> dict[object, np.ndarray]:
    if coordinates is not None:
        coords = np.asarray(coordinates, dtype=float)
        if coords.ndim != 2:
            raise ValueError("coordinates must be a 2D array")
        return {node: coords[int(node)] for node in graph.nodes}
    nodes = list(graph.nodes)
    n_nodes = len(nodes)
    if topology == "chain":
        midpoint = 0.5 * (n_nodes - 1)
        return {node: np.array([float(index) - midpoint, 0.0]) for index, node in enumerate(nodes)}
    if topology in {"ring", "complete"}:
        radius = 1.15
        angles = np.linspace(np.pi / 2.0, np.pi / 2.0 - 2.0 * np.pi, n_nodes, endpoint=False)
        return {
            node: radius * np.array([np.cos(angle), np.sin(angle)], dtype=float)
            for node, angle in zip(nodes, angles, strict=True)
        }
    return nx.spring_layout(graph, seed=13)


def sink_position(positions: dict[object, np.ndarray], trap_site: int) -> np.ndarray:
    trap = np.asarray(positions[trap_site], dtype=float)
    center = np.mean(np.stack([np.asarray(pos, dtype=float) for pos in positions.values()]), axis=0)
    direction = trap - center
    norm = np.linalg.norm(direction)
    if norm < 1e-9:
        direction = np.array([1.0, 0.0], dtype=float)
    else:
        direction = direction / norm
    return trap + 0.65 * direction


def loss_position(positions: dict[object, np.ndarray], trap_site: int) -> np.ndarray:
    trap = np.asarray(positions[trap_site], dtype=float)
    return trap + np.array([0.0, -0.85], dtype=float)


def _role_node_style(node: int, trap_site: int, initial_site: int) -> tuple[str, str, float]:
    if node == trap_site and node == initial_site:
        return "#f59e0b", "#7c2d12", 2.8
    if node == trap_site:
        return "#fca5a5", "#b91c1c", 2.6
    if node == initial_site:
        return "#93c5fd", "#1d4ed8", 2.6
    return "#cbd5e1", "#334155", 1.2


def _graph_legend_handles() -> list[Line2D]:
    return [
        Line2D([0], [0], marker="o", color="w", label="regular node", markerfacecolor="#cbd5e1", markeredgecolor="#334155", markersize=10),
        Line2D([0], [0], marker="o", color="w", label="initial site", markerfacecolor="#93c5fd", markeredgecolor="#1d4ed8", markersize=10),
        Line2D([0], [0], marker="o", color="w", label="trap site", markerfacecolor="#fca5a5", markeredgecolor="#b91c1c", markersize=10),
        Line2D([0], [0], marker="s", color="w", label="sink S", markerfacecolor="#111827", markeredgecolor="#0f172a", markersize=10),
        Line2D([0], [0], marker="D", color="w", label="loss L", markerfacecolor="#991b1b", markeredgecolor="#7f1d1d", markersize=9),
        Line2D([0], [0], ls="--", color="#111827", label="capture channel"),
    ]


def _graph_note() -> str:
    return (
        "Graph variables:\n"
        "node i = basis state |i>\n"
        "solid edge = coherent coupling J\n"
        "S = sink population $\\rho_{ss}$\n"
        "L = loss population $\\rho_{\\ell\\ell}$"
    )


def _site_energy_note(site_energies_hz: np.ndarray | None) -> str:
    if site_energies_hz is None:
        return "site energies: all $\\epsilon_i=0$"
    if np.allclose(site_energies_hz, 0.0):
        return "site energies: all $\\epsilon_i=0$"
    joined = ", ".join([f"$\\epsilon_{idx}={value:.2f}$" for idx, value in enumerate(np.asarray(site_energies_hz, dtype=float))])
    return f"site energies: {joined}"


def save_graph_topology_figure(
    path: Path,
    scenario_name: str,
    adjacency: np.ndarray,
    topology: str,
    trap_site: int,
    initial_site: int,
    site_energies_hz: np.ndarray | None = None,
    coupling_hz: float | None = None,
    sink_rate_hz: float | None = None,
    loss_rate_hz: float | None = None,
    coordinates: np.ndarray | None = None,
) -> None:
    graph = build_graph_from_adjacency(adjacency)
    pos = graph_positions(graph, topology, coordinates=coordinates)
    sink_pos = sink_position(pos, trap_site)
    l_pos = loss_position(pos, trap_site)

    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    node_colors = []
    node_sizes = []
    edge_colors = []
    line_widths = []
    for node in graph.nodes:
        fill, edge, width = _role_node_style(node, trap_site, initial_site)
        node_colors.append(fill)
        edge_colors.append(edge)
        line_widths.append(width)
        node_sizes.append(620 if node not in {trap_site, initial_site} else 720)

    edge_kwargs = {"width": 1.8, "edge_color": "#64748b", "alpha": 0.78}
    if topology == "complete":
        edge_kwargs["width"] = 1.2
        edge_kwargs["alpha"] = 0.42
    nx.draw_networkx_edges(graph, pos, ax=ax, **edge_kwargs)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=node_colors, node_size=node_sizes, linewidths=line_widths, edgecolors=edge_colors)
    nx.draw_networkx_labels(graph, pos, ax=ax, labels={node: str(node) for node in graph.nodes}, font_color="white")

    if topology in {"chain", "ring"}:
        edge_labels = {(u, v): f"J={coupling_hz:.2f}" if coupling_hz is not None else "J" for u, v in graph.edges}
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, ax=ax, font_size=8, font_color="#334155")

    for node, node_pos in pos.items():
        energy_value = 0.0 if site_energies_hz is None else float(np.asarray(site_energies_hz, dtype=float)[node])
        ax.text(
            node_pos[0],
            node_pos[1] - 0.22,
            f"$\\epsilon_{node}={energy_value:.2f}$",
            ha="center",
            va="top",
            fontsize=8,
            color="#0f172a",
        )

    ax.scatter([sink_pos[0]], [sink_pos[1]], s=650, marker="s", c="#111827", edgecolors="#0f172a")
    ax.scatter([l_pos[0]], [l_pos[1]], s=540, marker="D", c="#991b1b", edgecolors="#7f1d1d")
    ax.text(sink_pos[0], sink_pos[1], "S", color="white", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(l_pos[0], l_pos[1], "L", color="white", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.plot(
        [pos[trap_site][0], sink_pos[0]],
        [pos[trap_site][1], sink_pos[1]],
        ls="--",
        lw=1.4,
        color="#111827",
    )

    ax.set_title(f"{scenario_name}\nTopology view")
    ax.legend(handles=_graph_legend_handles(), frameon=True, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, -0.13), ncol=3)
    ax.text(
        0.02,
        0.98,
        _graph_note()
        + "\n"
        + _site_energy_note(site_energies_hz)
        + (
            f"\n$\\kappa={sink_rate_hz:.2f}$, $\\Gamma={loss_rate_hz:.2f}$"
            if sink_rate_hz is not None and loss_rate_hz is not None
            else ""
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.95},
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_graph_topology_overview(
    path: Path,
    scenarios: list[dict[str, object]],
) -> None:
    fig, axes = plt.subplots(1, len(scenarios), figsize=(5.0 * len(scenarios), 4.5))
    if len(scenarios) == 1:
        axes = np.array([axes])

    for axis, scenario in zip(axes, scenarios, strict=True):
        graph = build_graph_from_adjacency(np.asarray(scenario["adjacency"], dtype=float))
        scenario_coordinates = None
        if "coordinates" in scenario and scenario["coordinates"] is not None:
            scenario_coordinates = np.asarray(scenario["coordinates"], dtype=float)
        pos = graph_positions(graph, str(scenario["topology"]), coordinates=scenario_coordinates)
        trap_site = int(scenario["trap_site"])
        initial_site = int(scenario["initial_site"])
        sink_pos = sink_position(pos, trap_site)
        l_pos = loss_position(pos, trap_site)

        node_colors = []
        node_sizes = []
        edge_colors = []
        line_widths = []
        for node in graph.nodes:
            fill, edge, width = _role_node_style(node, trap_site, initial_site)
            node_colors.append(fill)
            edge_colors.append(edge)
            line_widths.append(width)
            node_sizes.append(620 if node not in {trap_site, initial_site} else 720)

        edge_kwargs = {"width": 1.8, "edge_color": "#64748b", "alpha": 0.78}
        if str(scenario["topology"]) == "complete":
            edge_kwargs["width"] = 1.2
            edge_kwargs["alpha"] = 0.42
        nx.draw_networkx_edges(graph, pos, ax=axis, **edge_kwargs)
        nx.draw_networkx_nodes(graph, pos, ax=axis, node_color=node_colors, node_size=node_sizes, linewidths=line_widths, edgecolors=edge_colors)
        nx.draw_networkx_labels(graph, pos, ax=axis, labels={node: str(node) for node in graph.nodes}, font_color="white")
        axis.scatter([sink_pos[0]], [sink_pos[1]], s=650, marker="s", c="#111827", edgecolors="#0f172a")
        axis.scatter([l_pos[0]], [l_pos[1]], s=540, marker="D", c="#991b1b", edgecolors="#7f1d1d")
        axis.text(sink_pos[0], sink_pos[1], "S", color="white", ha="center", va="center", fontsize=11, fontweight="bold")
        axis.text(l_pos[0], l_pos[1], "L", color="white", ha="center", va="center", fontsize=10, fontweight="bold")
        axis.plot(
            [pos[trap_site][0], sink_pos[0]],
            [pos[trap_site][1], sink_pos[1]],
            ls="--",
            lw=1.4,
            color="#111827",
        )
        axis.set_title(str(scenario["name"]))
        axis.set_axis_off()
        axis.text(
            0.02,
            0.98,
            "blue = initial\nred = trap\nsolid edge = J\nS = sink\nL = loss",
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.9},
        )

    fig.suptitle("Graph topologies used in the current transport baseline", y=1.02)
    fig.legend(handles=_graph_legend_handles(), frameon=True, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, -0.05), ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_population_animation_gif(
    path: Path,
    scenario_name: str,
    adjacency: np.ndarray,
    topology: str,
    trap_site: int,
    initial_site: int,
    states: np.ndarray,
    sink_population: np.ndarray,
    loss_population: np.ndarray,
    times: np.ndarray,
    dephasing_rate_hz: float,
    stride: int,
    fps: int,
    site_energies_hz: np.ndarray | None = None,
    coupling_hz: float | None = None,
    sink_rate_hz: float | None = None,
    loss_rate_hz: float | None = None,
    coordinates: np.ndarray | None = None,
) -> None:
    graph = build_graph_from_adjacency(adjacency)
    pos = graph_positions(graph, topology, coordinates=coordinates)
    s_pos = sink_position(pos, trap_site)
    l_pos = loss_position(pos, trap_site)

    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    frame_indices = list(range(0, len(times), max(1, stride)))
    if frame_indices[-1] != len(times) - 1:
        frame_indices.append(len(times) - 1)

    def _draw(frame_number: int) -> None:
        frame = frame_indices[frame_number]
        ax.clear()
        physical_pop = np.real(np.diag(states[frame])[: adjacency.shape[0]])
        node_colors = plt.cm.viridis(np.clip(physical_pop, 0.0, 1.0))
        node_sizes = 450 + 1100 * np.clip(physical_pop, 0.0, 1.0)
        edge_colors = []
        line_widths = []
        for node in graph.nodes:
            _, edge, width = _role_node_style(node, trap_site, initial_site)
            edge_colors.append(edge)
            line_widths.append(width)

        edge_kwargs = {"width": 1.8, "edge_color": "#64748b", "alpha": 0.78}
        if topology == "complete":
            edge_kwargs["width"] = 1.2
            edge_kwargs["alpha"] = 0.42
        nx.draw_networkx_edges(graph, pos, ax=ax, **edge_kwargs)
        nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=node_colors, node_size=node_sizes, linewidths=line_widths, edgecolors=edge_colors)
        nx.draw_networkx_labels(graph, pos, ax=ax, labels={node: str(node) for node in graph.nodes}, font_color="white")

        for node, node_pos in pos.items():
            energy_value = 0.0 if site_energies_hz is None else float(np.asarray(site_energies_hz, dtype=float)[node])
            ax.text(
                node_pos[0],
                node_pos[1] - 0.20,
                f"$\\epsilon_{node}={energy_value:.2f}$",
                ha="center",
                va="top",
                fontsize=7.5,
                color="#0f172a",
            )

        sink_color = plt.cm.inferno(float(np.clip(sink_population[frame], 0.0, 1.0)))
        loss_color = plt.cm.Reds(float(np.clip(loss_population[frame], 0.0, 1.0)))
        ax.scatter([s_pos[0]], [s_pos[1]], s=700 + 700 * sink_population[frame], marker="s", c=[sink_color], edgecolors="#0f172a")
        ax.scatter([l_pos[0]], [l_pos[1]], s=620 + 620 * loss_population[frame], marker="D", c=[loss_color], edgecolors="#7f1d1d")
        ax.text(s_pos[0], s_pos[1], "S", color="white", ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(l_pos[0], l_pos[1], "L", color="white", ha="center", va="center", fontsize=11, fontweight="bold")
        ax.plot([pos[trap_site][0], s_pos[0]], [pos[trap_site][1], s_pos[1]], ls="--", lw=1.4, color="#111827")

        info_text = (
            f"t = {times[frame]:.2f}\n"
            f"gamma_phi = {dephasing_rate_hz:.3f}\n"
            + (f"J = {coupling_hz:.2f}\n" if coupling_hz is not None else "")
            + (f"kappa = {sink_rate_hz:.2f}\n" if sink_rate_hz is not None else "")
            + (f"Gamma = {loss_rate_hz:.2f}\n" if loss_rate_hz is not None else "")
            + "P_i(t): node color/size\n"
            + f"rho_ss = {sink_population[frame]:.3f}\n"
            + f"rho_ll = {loss_population[frame]:.3f}"
        )

        ax.text(
            0.02,
            0.98,
            info_text,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.9},
        )
        ax.text(
            0.98,
            0.98,
            "S: sink\nL: loss\nblue outline: initial\nred outline: trap\nnode text: site energy",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8.5,
            bbox={"boxstyle": "round", "fc": "white", "ec": "#94a3b8", "alpha": 0.9},
        )
        ax.set_title(f"{scenario_name}\nPopulation evolution on the graph")
        ax.set_axis_off()

    animation = FuncAnimation(fig, _draw, frames=len(frame_indices), interval=max(40, int(1000 / max(1, fps))), repeat=True)
    animation.save(path, writer=PillowWriter(fps=max(1, fps)))
    plt.close(fig)
