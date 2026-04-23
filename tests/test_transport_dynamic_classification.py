from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np

from oqs_transport import (
    SUPPORTED_DYNAMIC_NETWORK_FAMILIES,
    classify_records,
    generate_network_instance,
    numeric_feature_names,
    signature_from_dephasing_scan,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
)
from scripts.run_transport_dynamic_classification_campaign import _profile_config, run_campaign


def test_dynamic_network_generators_are_valid() -> None:
    for family in SUPPORTED_DYNAMIC_NETWORK_FAMILIES:
        instance = generate_network_instance(family, n_sites=8, seed=123, realization_index=0)
        assert instance.adjacency.shape == (8, 8)
        assert instance.coordinates.shape == (8, 2)
        assert np.allclose(instance.adjacency, instance.adjacency.T)
        assert np.allclose(np.diag(instance.adjacency), 0.0)
        assert np.all(np.isfinite(instance.coordinates))


def test_topology_metrics_and_targets_are_finite() -> None:
    instance = generate_network_instance("watts_strogatz_small_world", n_sites=8, seed=5)
    candidates = target_candidates(instance, initial_site=7)
    assert {"near", "far", "high_centrality", "low_centrality"} <= set(candidates)
    metrics = topology_metrics(instance, initial_site=7, trap_site=candidates["far"])
    assert metrics["n_sites"] == 8.0
    assert all(np.isfinite(value) for value in metrics.values())


def test_dynamic_signature_is_finite_for_tiny_scan() -> None:
    instance = generate_network_instance("chain", n_sites=5, seed=1)
    candidates = target_candidates(instance, initial_site=4)
    trap_site = candidates["far"]
    topo = topology_metrics(instance, initial_site=4, trap_site=trap_site)
    times = np.linspace(0.0, 4.0, 32)
    energies = static_disorder_energies(5, 0.1, seed=2)
    scan = [
        simulate_transport(
            adjacency=instance.adjacency,
            coupling_hz=1.0,
            dephasing_rate_hz=gamma,
            sink_rate_hz=0.5,
            loss_rate_hz=0.01,
            times=times,
            initial_site=4,
            trap_site=trap_site,
            site_energies_hz=energies,
            node_coordinates=instance.coordinates,
        )
        for gamma in [0.0, 0.2]
    ]
    record = signature_from_dephasing_scan(
        scan_results=scan,
        dephasing_over_coupling=[0.0, 0.2],
        coupling_hz=1.0,
        family="chain",
        instance_id=instance.instance_id,
        graph_seed=1,
        disorder_seed=2,
        disorder_strength_over_coupling=0.1,
        target_style="far",
        initial_site=4,
        trap_site=trap_site,
        topology=topo,
    )
    numeric_values = [value for value in record.values() if isinstance(value, float)]
    assert numeric_values
    assert all(np.isfinite(value) for value in numeric_values)


def test_interpretable_classifier_runs_on_synthetic_records() -> None:
    records = []
    for index in range(12):
        family = "chain" if index < 6 else "ring"
        offset = 0.0 if family == "chain" else 2.0
        records.append(
            {
                "record_id": f"r{index}",
                "family": family,
                "best_arrival": offset + index * 0.01,
                "dephasing_gain": offset + 0.1,
                "topology_mean_degree": offset + 1.0,
            }
        )
    result = classify_records(records, feature_names=["best_arrival", "dephasing_gain", "topology_mean_degree"])
    assert result.accuracy >= result.baseline_accuracy
    assert result.confusion_matrix
    assert result.feature_importance


def test_dynamic_classification_campaign_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_dynamic_classification"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = _profile_config("smoke")
        config["families"] = ["chain", "ring"]
        config["n_sites_values"] = [5]
        config["disorder_seeds"] = [3]
        config["disorder_strength_over_coupling"] = [0.0]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["far"]
        config["t_final"] = 4.0
        config["n_time_samples"] = 32
        metrics = run_campaign(config, tmp_dir)
        assert metrics["record_count"] == 2
        assert (tmp_dir / "dynamic_signatures.csv").exists()
        assert (tmp_dir / "classification_report.json").exists()
        assert (tmp_dir / "summary.md").exists()
        assert (tmp_dir / "figures" / "confusion_matrix.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

