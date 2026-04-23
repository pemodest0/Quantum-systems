from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm


@dataclass(frozen=True)
class ClassicalTransportResult:
    times: np.ndarray
    node_populations: np.ndarray
    sink_population: np.ndarray
    loss_population: np.ndarray
    network_population: np.ndarray
    transport_efficiency: float
    sink_hitting_time: float | None
    transfer_time_to_threshold: float | None
    max_population_closure_error: float
    initial_site: int
    trap_site: int


def _threshold_crossing_time(times: np.ndarray, signal: np.ndarray, threshold: float) -> float | None:
    above = np.flatnonzero(np.asarray(signal, dtype=float) >= float(threshold))
    if above.size == 0:
        return None
    return float(np.asarray(times, dtype=float)[int(above[0])])


def _classical_generator(
    adjacency: np.ndarray,
    *,
    hopping_rate_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
    trap_site: int,
) -> np.ndarray:
    adjacency = np.asarray(adjacency, dtype=float)
    n_sites = adjacency.shape[0]
    dim = n_sites + 2
    sink_index = n_sites
    loss_index = n_sites + 1
    generator = np.zeros((dim, dim), dtype=float)
    strengths = np.sum(np.clip(adjacency, 0.0, None), axis=1)
    for source in range(n_sites):
        if strengths[source] > 1e-14:
            rates = float(hopping_rate_hz) * np.clip(adjacency[source], 0.0, None) / strengths[source]
            for target in range(n_sites):
                if target == source or rates[target] <= 0.0:
                    continue
                generator[target, source] += rates[target]
                generator[source, source] -= rates[target]
        if loss_rate_hz > 0.0:
            generator[loss_index, source] += float(loss_rate_hz)
            generator[source, source] -= float(loss_rate_hz)
    if sink_rate_hz > 0.0:
        generator[sink_index, int(trap_site)] += float(sink_rate_hz)
        generator[int(trap_site), int(trap_site)] -= float(sink_rate_hz)
    return generator


def simulate_classical_transport(
    adjacency: np.ndarray,
    *,
    hopping_rate_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
    times: np.ndarray,
    initial_site: int,
    trap_site: int,
    sink_hit_threshold: float = 0.1,
    transfer_threshold: float = 0.5,
) -> ClassicalTransportResult:
    adjacency = np.asarray(adjacency, dtype=float)
    n_sites = adjacency.shape[0]
    dim = n_sites + 2
    initial = np.zeros(dim, dtype=float)
    initial[int(initial_site)] = 1.0
    generator = _classical_generator(
        adjacency,
        hopping_rate_hz=hopping_rate_hz,
        sink_rate_hz=sink_rate_hz,
        loss_rate_hz=loss_rate_hz,
        trap_site=trap_site,
    )
    times = np.asarray(times, dtype=float)
    populations = np.asarray([expm(generator * float(time)) @ initial for time in times], dtype=float)
    populations = np.clip(populations, 0.0, 1.0)
    node_populations = populations[:, :n_sites]
    sink_population = populations[:, n_sites]
    loss_population = populations[:, n_sites + 1]
    network_population = np.sum(node_populations, axis=1)
    closure_error = np.abs(np.sum(populations, axis=1) - 1.0)
    return ClassicalTransportResult(
        times=times,
        node_populations=node_populations,
        sink_population=sink_population,
        loss_population=loss_population,
        network_population=network_population,
        transport_efficiency=float(np.clip(sink_population[-1], 0.0, 1.0)),
        sink_hitting_time=_threshold_crossing_time(times, sink_population, sink_hit_threshold),
        transfer_time_to_threshold=_threshold_crossing_time(times, sink_population, transfer_threshold),
        max_population_closure_error=float(np.max(closure_error)),
        initial_site=int(initial_site),
        trap_site=int(trap_site),
    )
