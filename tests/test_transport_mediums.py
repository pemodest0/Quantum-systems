from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from oqs_transport import (
    build_medium_definition,
    classify_regime,
    load_medium_campaign_config,
)
from oqs_transport.simulation import simulate_transport


def _local_tmp_path(filename: str) -> Path:
    tmp_dir = Path(__file__).resolve().parent / "_tmp_transport_medium"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / filename


def test_build_medium_definition_chain_and_square_lattice() -> None:
    chain = build_medium_definition(
        medium_type="chain_1d",
        coupling_law="nearest_neighbor",
        length_scale=1.0,
        disorder_strength_hz=0.0,
        site_energy_profile="uniform",
        n_sites=5,
    )
    assert chain.coordinates.shape == (5, 2)
    assert chain.adjacency.shape == (5, 5)
    assert np.allclose(np.diag(chain.adjacency), 0.0)
    assert np.isclose(np.sum(chain.adjacency) / 2.0, 4.0)

    square = build_medium_definition(
        medium_type="square_lattice_2d",
        coupling_law="nearest_neighbor",
        length_scale=1.0,
        disorder_strength_hz=0.0,
        site_energy_profile="uniform",
        n_rows=3,
        n_cols=3,
    )
    assert square.coordinates.shape == (9, 2)
    assert square.adjacency.shape == (9, 9)
    assert np.allclose(square.adjacency, square.adjacency.T)


def test_simulate_transport_spatial_observables_are_finite() -> None:
    medium = build_medium_definition(
        medium_type="chain_1d",
        coupling_law="nearest_neighbor",
        length_scale=1.0,
        disorder_strength_hz=0.0,
        site_energy_profile="uniform",
        n_sites=4,
    )
    times = np.linspace(0.0, 8.0, 80)
    result = simulate_transport(
        adjacency=medium.adjacency,
        coupling_hz=1.0,
        dephasing_rate_hz=0.1,
        sink_rate_hz=0.5,
        loss_rate_hz=0.0,
        times=times,
        initial_site=3,
        trap_site=0,
        site_energies_hz=medium.site_energies_hz,
        node_coordinates=medium.coordinates,
        sink_hit_threshold=0.05,
        transfer_threshold=0.25,
        interface_axis=0,
        interface_position=1.5,
    )
    assert result.mean_position_t is not None
    assert result.mean_squared_displacement_t is not None
    assert result.front_width_t is not None
    assert result.interface_current_t is not None
    assert result.spatial_observable_context == "graph_normalized"
    assert result.mean_position_t.shape == (len(times), 2)
    assert np.all(np.isfinite(result.mean_squared_displacement_t))
    assert np.all(result.mean_squared_displacement_t >= 0.0)
    assert np.all(np.isfinite(result.front_width_t))


def test_classify_regime_identifies_dephasing_assistance() -> None:
    classification = classify_regime(
        transport_efficiency=0.72,
        coherent_efficiency_reference=0.60,
        best_efficiency_reference=0.72,
        final_loss_population=0.05,
        disorder_strength_over_coupling=0.4,
        dephasing_over_coupling=0.2,
        mean_coherence_l1=0.18,
        final_participation_ratio=3.0,
        final_entropy=0.8,
        final_mean_squared_displacement=2.5,
        max_mean_squared_displacement_reference=2.8,
        n_sites=6,
    )
    assert classification.label == "dephasing-assisted"
    assert classification.confidence > 0.4


def test_load_medium_campaign_config_reads_medium_block() -> None:
    config_path = _local_tmp_path("medium_config.json")
    config_path.write_text(
        json.dumps(
            {
                "study_name": "Medium test",
                "output_subdir": "tmp_medium",
                "time_grid": {"t_final": 10.0, "n_samples": 100},
                "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
                "sweep": {
                    "disorder_strength_over_coupling": [0.0, 0.2],
                    "dephasing_over_coupling": [0.0, 0.1],
                },
                "ensemble_seeds": [3, 5],
                "scenarios": [
                    {
                        "name": "Test chain",
                        "coupling_hz": 1.0,
                        "sink_rate_hz": 0.5,
                        "loss_rate_hz": 0.02,
                        "initial_site": 3,
                        "trap_site": 0,
                        "medium": {
                            "medium_type": "chain_1d",
                            "n_sites": 4,
                            "length_scale": 1.0,
                            "coupling_law": "nearest_neighbor",
                            "site_energy_profile": "static_disorder",
                            "sink_definition": {"mode": "single_site", "site_index": 0},
                            "loss_definition": {"mode": "uniform_local_loss"},
                            "interface_axis": "x",
                            "interface_position": 1.5,
                        },
                        "literature_expectation": {
                            "expected_transport_trend": "trend",
                            "expected_role_of_disorder": "disorder",
                            "expected_role_of_phase_scrambling": "phase",
                            "expected_failure_mode": "failure",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_medium_campaign_config(config_path)
    assert config.study_name == "Medium test"
    assert len(config.scenarios) == 1
    assert config.scenarios[0].medium.medium_type == "chain_1d"
    assert config.scenarios[0].medium.interface_axis == "x"
