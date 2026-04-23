from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from oqs_control.open_systems.lindblad import mesolve
from oqs_control.open_systems.statistical_mechanics import purity, von_neumann_entropy

from .networks import tight_binding_hamiltonian


@dataclass(frozen=True)
class TransportSimulationResult:
    times: np.ndarray
    states: np.ndarray
    node_populations: np.ndarray
    node_coordinates: np.ndarray | None
    sink_population: np.ndarray
    loss_population: np.ndarray
    network_population: np.ndarray
    purity_t: np.ndarray
    entropy_t: np.ndarray
    population_shannon_entropy_t: np.ndarray
    participation_ratio_t: np.ndarray
    ipr_t: np.ndarray
    spatial_observable_context: str
    mean_position_t: np.ndarray | None
    mean_squared_displacement_t: np.ndarray | None
    front_width_t: np.ndarray | None
    interface_current_t: np.ndarray | None
    integrated_interface_current: float | None
    sink_hitting_time: float | None
    transfer_time_to_threshold: float | None
    sink_hit_threshold: float
    transfer_threshold: float
    interface_axis: int | None
    interface_position: float | None
    transport_efficiency: float
    mean_coherence_l1: float
    final_purity: float
    final_entropy: float
    final_population_shannon_entropy: float
    final_participation_ratio: float
    final_ipr: float
    max_trace_deviation: float
    max_population_closure_error: float
    min_state_eigenvalue: float
    trap_site: int
    sink_index: int
    loss_index: int
    initial_site: int
    dephasing_rate_hz: float


def _basis(dim: int, index: int) -> np.ndarray:
    state = np.zeros((dim, 1), dtype=complex)
    state[index, 0] = 1.0
    return state


def _projector(dim: int, index: int) -> np.ndarray:
    ket = _basis(dim, index)
    return ket @ ket.conj().T


def _l1_coherence(rho: np.ndarray) -> float:
    off_diagonal = rho - np.diag(np.diag(rho))
    return float(np.sum(np.abs(off_diagonal)))


def _population_closure_error(states: np.ndarray) -> np.ndarray:
    diagonal = np.real(np.diagonal(states, axis1=1, axis2=2))
    return np.abs(np.sum(diagonal, axis=1) - 1.0)


def _trace_deviation(states: np.ndarray) -> np.ndarray:
    traces = np.real_if_close(np.trace(states, axis1=1, axis2=2)).astype(float)
    return np.abs(traces - 1.0)


def _minimum_state_eigenvalue(states: np.ndarray) -> float:
    minima: list[float] = []
    for rho in states:
        hermitian = 0.5 * (rho + rho.conj().T)
        minima.append(float(np.min(np.linalg.eigvalsh(hermitian)).real))
    return float(min(minima))


def _conditional_network_state(rho: np.ndarray, n_sites: int) -> np.ndarray:
    network_state = 0.5 * (rho[:n_sites, :n_sites] + rho[:n_sites, :n_sites].conj().T)
    weight = float(np.real_if_close(np.trace(network_state)).real)
    if weight <= 1e-14:
        return np.zeros_like(network_state)
    return network_state / weight


def _normalized_node_populations(rho: np.ndarray, n_sites: int) -> np.ndarray:
    populations = np.real(np.diag(rho[:n_sites, :n_sites])).astype(float)
    total = float(np.sum(populations))
    if total <= 1e-14:
        return np.zeros_like(populations)
    return populations / total


def _population_shannon_entropy(probabilities: np.ndarray) -> float:
    p = np.asarray(probabilities, dtype=float)
    p = np.clip(p, 0.0, None)
    total = float(np.sum(p))
    if total <= 1e-14:
        return 0.0
    p = p / total
    nz = p > 0.0
    return float(-np.sum(p[nz] * np.log(p[nz])))


def _inverse_participation_ratio(probabilities: np.ndarray) -> float:
    p = np.asarray(probabilities, dtype=float)
    p = np.clip(p, 0.0, None)
    total = float(np.sum(p))
    if total <= 1e-14:
        return 0.0
    p = p / total
    return float(np.sum(p**2))


def _participation_ratio(probabilities: np.ndarray) -> float:
    ipr = _inverse_participation_ratio(probabilities)
    if ipr <= 1e-14:
        return 0.0
    return float(1.0 / ipr)


def _threshold_crossing_time(times: np.ndarray, signal: np.ndarray, threshold: float) -> float | None:
    above = np.flatnonzero(np.asarray(signal, dtype=float) >= float(threshold))
    if above.size == 0:
        return None
    return float(np.asarray(times, dtype=float)[int(above[0])])


def _spatial_observables(
    *,
    states: np.ndarray,
    times: np.ndarray,
    node_coordinates: np.ndarray | None,
    initial_site: int,
    adjacency: np.ndarray,
    coupling_hz: float,
    interface_axis: int | None,
    interface_position: float | None,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None, float | None]:
    if node_coordinates is None:
        return None, None, None, None, None

    coordinates = np.asarray(node_coordinates, dtype=float)
    if coordinates.ndim != 2:
        raise ValueError("node_coordinates must be a 2D array")
    n_sites = coordinates.shape[0]
    normalized_populations = np.array([_normalized_node_populations(rho, n_sites) for rho in states], dtype=float)
    mean_position_t = normalized_populations @ coordinates
    initial_position = coordinates[int(initial_site)]
    displacements = coordinates[None, :, :] - initial_position[None, None, :]
    squared_distances = np.sum(displacements**2, axis=2)
    mean_squared_displacement_t = np.sum(normalized_populations * squared_distances, axis=1)
    centered = coordinates[None, :, :] - mean_position_t[:, None, :]
    front_width_t = np.sqrt(np.sum(normalized_populations * np.sum(centered**2, axis=2), axis=1))

    interface_current_t: np.ndarray | None = None
    integrated_interface_current: float | None = None
    if interface_axis is not None and interface_position is not None:
        interface_current_t = np.zeros(len(times), dtype=float)
        axis = int(interface_axis)
        threshold = float(interface_position)
        left_mask = coordinates[:, axis] <= threshold
        right_mask = coordinates[:, axis] > threshold
        hamiltonian = tight_binding_hamiltonian(adjacency, coupling_hz, site_energies_hz=None)
        crossing_pairs: list[tuple[int, int]] = []
        for i in range(n_sites):
            for j in range(n_sites):
                if not left_mask[i] or not right_mask[j]:
                    continue
                if np.abs(adjacency[i, j]) > 0.0:
                    crossing_pairs.append((i, j))
        for time_index, rho in enumerate(states):
            rho_nodes = rho[:n_sites, :n_sites]
            current = 0.0
            for left_site, right_site in crossing_pairs:
                current += 2.0 * float(np.imag(hamiltonian[left_site, right_site] * rho_nodes[right_site, left_site]))
            interface_current_t[time_index] = current
        integrated_interface_current = float(np.trapezoid(np.clip(interface_current_t, 0.0, None), x=times))

    return (
        mean_position_t,
        mean_squared_displacement_t,
        front_width_t,
        interface_current_t,
        integrated_interface_current,
    )


def _jump_operators(
    n_sites: int,
    trap_site: int,
    sink_index: int,
    loss_index: int,
    dephasing_rate_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
) -> list[np.ndarray]:
    jumps: list[np.ndarray] = []
    dim = n_sites + 2
    for site in range(n_sites):
        if dephasing_rate_hz > 0.0:
            jumps.append(np.sqrt(dephasing_rate_hz) * _projector(dim, site))
        if loss_rate_hz > 0.0:
            jumps.append(np.sqrt(loss_rate_hz) * (_basis(dim, loss_index) @ _basis(dim, site).conj().T))
    jumps.append(np.sqrt(sink_rate_hz) * (_basis(dim, sink_index) @ _basis(dim, trap_site).conj().T))
    return jumps


def simulate_transport(
    adjacency: np.ndarray,
    coupling_hz: float,
    dephasing_rate_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
    times: np.ndarray,
    initial_site: int,
    trap_site: int,
    site_energies_hz: np.ndarray | None = None,
    node_coordinates: np.ndarray | None = None,
    sink_hit_threshold: float = 0.1,
    transfer_threshold: float = 0.5,
    interface_axis: int | None = None,
    interface_position: float | None = None,
) -> TransportSimulationResult:
    adjacency = np.asarray(adjacency, dtype=float)
    n_sites = adjacency.shape[0]
    if initial_site < 0 or initial_site >= n_sites:
        raise ValueError("initial_site out of range")
    if trap_site < 0 or trap_site >= n_sites:
        raise ValueError("trap_site out of range")

    hamiltonian = tight_binding_hamiltonian(adjacency, coupling_hz, site_energies_hz)
    dim = n_sites + 2
    h_aug = np.zeros((dim, dim), dtype=complex)
    h_aug[:n_sites, :n_sites] = hamiltonian

    rho0 = _projector(dim, initial_site)
    sink_index = n_sites
    loss_index = n_sites + 1
    jumps = _jump_operators(
        n_sites=n_sites,
        trap_site=trap_site,
        sink_index=sink_index,
        loss_index=loss_index,
        dephasing_rate_hz=dephasing_rate_hz,
        sink_rate_hz=sink_rate_hz,
        loss_rate_hz=loss_rate_hz,
    )
    solved = mesolve(h_aug, rho0, np.asarray(times, dtype=float), jumps)
    node_populations = np.real(np.diagonal(solved.states[:, :n_sites, :n_sites], axis1=1, axis2=2)).astype(float)
    sink_population = np.real_if_close(solved.states[:, sink_index, sink_index]).astype(float)
    loss_population = np.real_if_close(solved.states[:, loss_index, loss_index]).astype(float)
    network_population = np.sum(node_populations, axis=1)
    mean_coherence_l1 = float(np.mean([_l1_coherence(rho[:n_sites, :n_sites]) for rho in solved.states]))
    conditional_states = [_conditional_network_state(rho, n_sites) for rho in solved.states]
    normalized_populations = [_normalized_node_populations(rho, n_sites) for rho in solved.states]
    purity_t = np.array([purity(rho) for rho in conditional_states], dtype=float)
    entropy_t = np.array([von_neumann_entropy(rho + 1e-12 * np.eye(n_sites)) for rho in conditional_states], dtype=float)
    population_shannon_entropy_t = np.array(
        [_population_shannon_entropy(probabilities) for probabilities in normalized_populations],
        dtype=float,
    )
    ipr_t = np.array([_inverse_participation_ratio(probabilities) for probabilities in normalized_populations], dtype=float)
    participation_ratio_t = np.array([_participation_ratio(probabilities) for probabilities in normalized_populations], dtype=float)
    (
        mean_position_t,
        mean_squared_displacement_t,
        front_width_t,
        interface_current_t,
        integrated_interface_current,
    ) = _spatial_observables(
        states=solved.states,
        times=solved.times,
        node_coordinates=node_coordinates,
        initial_site=initial_site,
        adjacency=adjacency,
        coupling_hz=coupling_hz,
        interface_axis=interface_axis,
        interface_position=interface_position,
    )
    final_network_state = conditional_states[-1]
    trace_deviation = _trace_deviation(solved.states)
    closure_error = _population_closure_error(solved.states)
    return TransportSimulationResult(
        times=solved.times,
        states=solved.states,
        node_populations=node_populations,
        node_coordinates=None if node_coordinates is None else np.asarray(node_coordinates, dtype=float),
        sink_population=sink_population,
        loss_population=loss_population,
        network_population=network_population,
        purity_t=purity_t,
        entropy_t=entropy_t,
        population_shannon_entropy_t=population_shannon_entropy_t,
        participation_ratio_t=participation_ratio_t,
        ipr_t=ipr_t,
        spatial_observable_context="graph_normalized",
        mean_position_t=mean_position_t,
        mean_squared_displacement_t=mean_squared_displacement_t,
        front_width_t=front_width_t,
        interface_current_t=interface_current_t,
        integrated_interface_current=integrated_interface_current,
        sink_hitting_time=_threshold_crossing_time(solved.times, sink_population, sink_hit_threshold),
        transfer_time_to_threshold=_threshold_crossing_time(solved.times, sink_population, transfer_threshold),
        sink_hit_threshold=float(sink_hit_threshold),
        transfer_threshold=float(transfer_threshold),
        interface_axis=interface_axis,
        interface_position=interface_position,
        transport_efficiency=float(np.clip(sink_population[-1], 0.0, 1.0)),
        mean_coherence_l1=mean_coherence_l1,
        final_purity=purity(final_network_state),
        final_entropy=von_neumann_entropy(final_network_state + 1e-12 * np.eye(n_sites)),
        final_population_shannon_entropy=float(population_shannon_entropy_t[-1]),
        final_participation_ratio=float(participation_ratio_t[-1]),
        final_ipr=float(ipr_t[-1]),
        max_trace_deviation=float(np.max(trace_deviation)),
        max_population_closure_error=float(np.max(closure_error)),
        min_state_eigenvalue=_minimum_state_eigenvalue(solved.states),
        trap_site=trap_site,
        sink_index=sink_index,
        loss_index=loss_index,
        initial_site=initial_site,
        dephasing_rate_hz=float(dephasing_rate_hz),
    )


def enaqt_scan(
    adjacency: np.ndarray,
    coupling_hz: float,
    dephasing_rates_hz: np.ndarray,
    sink_rate_hz: float,
    loss_rate_hz: float,
    times: np.ndarray,
    initial_site: int,
    trap_site: int,
    site_energies_hz: np.ndarray | None = None,
    node_coordinates: np.ndarray | None = None,
    sink_hit_threshold: float = 0.1,
    transfer_threshold: float = 0.5,
    interface_axis: int | None = None,
    interface_position: float | None = None,
) -> list[TransportSimulationResult]:
    return [
        simulate_transport(
            adjacency=adjacency,
            coupling_hz=coupling_hz,
            dephasing_rate_hz=float(rate),
            sink_rate_hz=sink_rate_hz,
            loss_rate_hz=loss_rate_hz,
            times=times,
            initial_site=initial_site,
            trap_site=trap_site,
            site_energies_hz=site_energies_hz,
            node_coordinates=node_coordinates,
            sink_hit_threshold=sink_hit_threshold,
            transfer_threshold=transfer_threshold,
            interface_axis=interface_axis,
            interface_position=interface_position,
        )
        for rate in np.asarray(dephasing_rates_hz, dtype=float)
    ]
