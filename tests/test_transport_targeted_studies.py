from __future__ import annotations

import numpy as np

from oqs_transport import chain_adjacency
from scripts.run_transport_targeted_studies import _graph_metrics, _ring_shortest_distance, _ring_unique_distances


def test_graph_metrics_for_chain_target_are_consistent() -> None:
    adjacency = chain_adjacency(5)
    metrics = _graph_metrics(adjacency, initial_site=4, trap_site=0)

    assert metrics["trap_degree"] == 1.0
    assert np.isclose(metrics["trap_closeness"], 0.4)
    assert np.isclose(metrics["mean_distance_to_trap"], 2.0)
    assert metrics["initial_to_trap_distance"] == 4.0


def test_ring_distance_helpers_match_shortest_path_geometry() -> None:
    assert _ring_unique_distances(4) == [1, 2]
    assert _ring_unique_distances(5) == [1, 2]
    assert _ring_shortest_distance(6, initial_site=0, trap_site=1) == 1
    assert _ring_shortest_distance(6, initial_site=0, trap_site=5) == 1
    assert _ring_shortest_distance(6, initial_site=0, trap_site=3) == 3
