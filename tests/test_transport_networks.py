from __future__ import annotations

import numpy as np

from oqs_transport import (
    chain_adjacency,
    complete_adjacency,
    enaqt_scan,
    ring_adjacency,
    simulate_transport,
)


def test_basic_adjacency_construction() -> None:
    chain = chain_adjacency(4)
    ring = ring_adjacency(4)
    complete = complete_adjacency(4)

    assert np.allclose(chain, chain.T)
    assert np.allclose(ring, ring.T)
    assert np.allclose(complete, complete.T)
    assert np.allclose(np.diag(complete), 0.0)
    assert np.sum(chain) == 6.0
    assert np.sum(ring) == 8.0
    assert np.sum(complete) == 12.0


def test_transport_trace_is_preserved_and_efficiency_is_bounded() -> None:
    times = np.linspace(0.0, 10.0, 240)
    result = simulate_transport(
        adjacency=chain_adjacency(4),
        coupling_hz=1.0,
        dephasing_rate_hz=0.2,
        sink_rate_hz=0.6,
        loss_rate_hz=0.02,
        times=times,
        initial_site=3,
        trap_site=0,
    )

    traces = np.real_if_close(np.trace(result.states, axis1=1, axis2=2))
    assert np.allclose(traces, 1.0, atol=1e-9)
    assert 0.0 <= result.transport_efficiency <= 1.0
    assert np.all(result.sink_population >= -1e-12)
    assert np.all(result.sink_population <= 1.0 + 1e-9)
    assert np.all(result.loss_population >= -1e-12)
    assert np.all(result.loss_population <= 1.0 + 1e-9)
    assert np.all(result.sink_population + result.loss_population <= 1.0 + 1e-9)
    assert result.node_populations.shape == (times.size, 4)
    assert np.all(result.network_population >= -1e-12)
    assert np.all(result.purity_t >= -1e-12)
    assert np.all(result.purity_t <= 1.0 + 1e-9)
    assert np.all(result.entropy_t >= -1e-12)
    assert np.all(result.population_shannon_entropy_t >= -1e-12)
    assert np.all(result.participation_ratio_t >= -1e-12)
    assert np.all(result.ipr_t >= -1e-12)
    assert np.all(result.ipr_t <= 1.0 + 1e-9)
    assert result.final_participation_ratio >= 0.0
    assert result.final_population_shannon_entropy >= 0.0


def test_complete_network_exhibits_noise_assisted_transport_window() -> None:
    times = np.linspace(0.0, 20.0, 360)
    rates = np.array([0.0, 0.2, 1.6, 6.4], dtype=float)
    scan = enaqt_scan(
        adjacency=complete_adjacency(4),
        coupling_hz=1.0,
        dephasing_rates_hz=rates,
        sink_rate_hz=0.7,
        loss_rate_hz=0.02,
        times=times,
        initial_site=1,
        trap_site=0,
    )
    efficiencies = np.array([case.transport_efficiency for case in scan], dtype=float)

    assert efficiencies[1] > efficiencies[0]
    assert efficiencies[2] > efficiencies[1]
    assert efficiencies[2] > efficiencies[3]
