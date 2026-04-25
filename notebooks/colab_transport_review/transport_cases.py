from __future__ import annotations

from collections.abc import Iterable

import networkx as nx
import numpy as np
import pandas as pd

from .transport_core import make_graph, simulate_classical_transport, simulate_open_quantum_transport


def choose_target(graph: nx.Graph, pos: dict[int, np.ndarray], initial_site: int, target_style: str = "far") -> int:
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


def dephasing_scan(
    family: str,
    *,
    n: int = 8,
    target_style: str = "far",
    W: float = 0.6,
    seed: int = 3,
    gamma_values: Iterable[float] | None = None,
    t_final: float = 12.0,
    n_times: int = 100,
) -> tuple[pd.DataFrame, nx.Graph, dict[int, np.ndarray], int, int]:
    gamma_values = list(gamma_values or [0.0, 0.03, 0.05, 0.1, 0.2, 0.4, 0.8, 1.2])
    graph, pos = make_graph(family, n=n, seed=seed)
    initial_site = min(graph.nodes, key=lambda i: (pos[i][0] + pos[i][1], i))
    target_site = choose_target(graph, pos, initial_site, target_style=target_style)

    rows: list[dict[str, float | int | str]] = []
    for gamma in gamma_values:
        quantum, _ = simulate_open_quantum_transport(
            graph,
            pos,
            initial_site=initial_site,
            target_site=target_site,
            disorder_strength_over_J=W,
            gamma_phi_over_J=float(gamma),
            seed=seed,
            t_final=t_final,
            n_times=n_times,
        )
        final = quantum.iloc[-1].to_dict()
        final.update(
            {
                "family": family,
                "n": graph.number_of_nodes(),
                "seed": seed,
                "W_over_J": W,
                "gamma_phi_over_J": float(gamma),
                "initial_site": initial_site,
                "target_site": target_site,
                "target_style": target_style,
            }
        )
        rows.append(final)

    df = pd.DataFrame(rows)
    zero = float(df.loc[df["gamma_phi_over_J"] == 0.0, "target_arrival"].iloc[0])
    df["gain_over_zero_dephasing"] = df["target_arrival"] - zero
    return df, graph, pos, initial_site, target_site


def target_placement_scan(
    family: str = "ring",
    *,
    n: int = 8,
    target_styles: Iterable[str] = ("near", "far", "high_centrality", "low_centrality"),
    W: float = 0.6,
    gamma: float = 0.1,
    seed: int = 3,
    t_final: float = 12.0,
    n_times: int = 120,
) -> tuple[pd.DataFrame, nx.Graph, dict[int, np.ndarray], int]:
    graph, pos = make_graph(family, n=n, seed=seed)
    initial_site = min(graph.nodes, key=lambda i: (pos[i][0] + pos[i][1], i))
    rows: list[dict[str, float | int | str]] = []

    for style in target_styles:
        target_site = choose_target(graph, pos, initial_site, target_style=style)
        quantum, _ = simulate_open_quantum_transport(
            graph,
            pos,
            initial_site=initial_site,
            target_site=target_site,
            disorder_strength_over_J=W,
            gamma_phi_over_J=gamma,
            seed=seed,
            t_final=t_final,
            n_times=n_times,
        )
        final = quantum.iloc[-1].to_dict()
        final.update(
            {
                "family": family,
                "n": graph.number_of_nodes(),
                "seed": seed,
                "target_style": style,
                "target_site": target_site,
                "W_over_J": W,
                "gamma_phi_over_J": gamma,
                "shortest_path_distance": nx.shortest_path_length(graph, initial_site, target_site),
                "target_closeness": nx.closeness_centrality(graph)[target_site],
                "target_degree": graph.degree[target_site],
            }
        )
        rows.append(final)
    return pd.DataFrame(rows), graph, pos, initial_site


def quantum_vs_classical_case(
    family: str = "ring",
    *,
    n: int = 8,
    W: float = 0.6,
    gamma: float = 0.1,
    seed: int = 3,
    target_style: str = "far",
    t_final: float = 12.0,
    n_times: int = 140,
) -> tuple[pd.DataFrame, dict[str, float | int | str], nx.Graph, dict[int, np.ndarray], int, int]:
    graph, pos = make_graph(family, n=n, seed=seed)
    initial_site = min(graph.nodes, key=lambda i: (pos[i][0] + pos[i][1], i))
    target_site = choose_target(graph, pos, initial_site, target_style=target_style)

    quantum, _ = simulate_open_quantum_transport(
        graph,
        pos,
        initial_site=initial_site,
        target_site=target_site,
        disorder_strength_over_J=W,
        gamma_phi_over_J=gamma,
        seed=seed,
        t_final=t_final,
        n_times=n_times,
    )
    classical = simulate_classical_transport(
        graph,
        initial_site=initial_site,
        target_site=target_site,
        t_final=t_final,
        n_times=n_times,
    )
    merged = quantum.merge(classical, on="time")
    summary = {
        "family": family,
        "n": n,
        "seed": seed,
        "target_style": target_style,
        "initial_site": initial_site,
        "target_site": target_site,
        "quantum_arrival": float(merged["target_arrival"].iloc[-1]),
        "classical_arrival": float(merged["target_arrival_classical"].iloc[-1]),
        "quantum_minus_classical": float(merged["target_arrival"].iloc[-1] - merged["target_arrival_classical"].iloc[-1]),
        "final_entropy": float(merged["von_neumann_entropy"].iloc[-1]),
    }
    return merged, summary, graph, pos, initial_site, target_site


def mini_seeded_campaign(
    *,
    families: Iterable[str] = ("chain", "ring", "star", "complete"),
    n: int = 8,
    seeds: Iterable[int] = (3, 5, 7, 11),
    gamma_values: Iterable[float] = (0.0, 0.05, 0.1, 0.2, 0.4),
    W: float = 0.6,
    target_style: str = "far",
    t_final: float = 10.0,
    n_times: int = 90,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for family in families:
        for seed in seeds:
            zero_arrival: float | None = None
            graph, pos = make_graph(family, n=n, seed=seed)
            initial_site = min(graph.nodes, key=lambda i: (pos[i][0] + pos[i][1], i))
            target_site = choose_target(graph, pos, initial_site, target_style=target_style)
            for gamma in gamma_values:
                quantum, _ = simulate_open_quantum_transport(
                    graph,
                    pos,
                    initial_site=initial_site,
                    target_site=target_site,
                    disorder_strength_over_J=W,
                    gamma_phi_over_J=float(gamma),
                    seed=seed,
                    t_final=t_final,
                    n_times=n_times,
                )
                final = quantum.iloc[-1]
                if float(gamma) == 0.0:
                    zero_arrival = float(final["target_arrival"])
                rows.append(
                    {
                        "family": family,
                        "seed": seed,
                        "n": n,
                        "target_style": target_style,
                        "gamma_phi_over_J": float(gamma),
                        "W_over_J": W,
                        "target_arrival": float(final["target_arrival"]),
                        "von_neumann_entropy": float(final["von_neumann_entropy"]),
                        "purity": float(final["purity"]),
                        "coherence_l1": float(final["coherence_l1"]),
                        "participation_ratio": float(final["participation_ratio"]),
                        "ipr": float(final["ipr"]),
                        "gain_over_zero_dephasing": float(final["target_arrival"]) - (zero_arrival if zero_arrival is not None else float(final["target_arrival"])),
                    }
                )
    return pd.DataFrame(rows)


def summarize_campaign(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("family", as_index=False).agg(
        arrival_mean=("target_arrival", "mean"),
        arrival_std=("target_arrival", "std"),
        entropy_mean=("von_neumann_entropy", "mean"),
        purity_mean=("purity", "mean"),
        coherence_mean=("coherence_l1", "mean"),
        participation_mean=("participation_ratio", "mean"),
        best_dephasing_gain=("gain_over_zero_dephasing", "max"),
    )
    return grouped.sort_values("arrival_mean", ascending=False).reset_index(drop=True)
