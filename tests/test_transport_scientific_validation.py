from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np

from oqs_transport import (
    chain_adjacency,
    classification_result_to_dict,
    classify_records,
    simulate_classical_transport,
)
from scripts.run_transport_scientific_validation import _profile_config, run_validation


def test_group_split_keeps_graph_instances_disjoint() -> None:
    records = []
    for label in ["a", "b"]:
        for group_index in range(4):
            for row in range(3):
                records.append(
                    {
                        "record_id": f"{label}_{group_index}_{row}",
                        "family": label,
                        "validation_group_id": f"{label}_g{group_index}",
                        "feature": float(group_index) + (10.0 if label == "b" else 0.0),
                    }
                )
    result = classify_records(
        records,
        feature_names=["feature"],
        split_strategy="group",
        group_key="validation_group_id",
        n_repeats=3,
        random_seed=3,
    )
    payload = classification_result_to_dict(result)
    assert np.isfinite(payload["accuracy_mean"])
    assert np.isfinite(payload["accuracy_ci95"][0])
    group_by_record = {record["record_id"]: record["validation_group_id"] for record in records}
    train_groups = {group_by_record[item["record_id"]] for item in payload["predictions"] if not item["is_test"]}
    test_groups = {group_by_record[item["record_id"]] for item in payload["predictions"] if item["is_test"]}
    assert train_groups.isdisjoint(test_groups)


def test_classical_transport_conserves_and_drains_population() -> None:
    times = np.linspace(0.0, 4.0, 20)
    adjacency = chain_adjacency(4)
    closed = simulate_classical_transport(
        adjacency,
        hopping_rate_hz=1.0,
        sink_rate_hz=0.0,
        loss_rate_hz=0.0,
        times=times,
        initial_site=3,
        trap_site=0,
    )
    assert closed.max_population_closure_error < 1e-10
    assert np.isclose(closed.network_population[-1], 1.0)
    open_result = simulate_classical_transport(
        adjacency,
        hopping_rate_hz=1.0,
        sink_rate_hz=0.7,
        loss_rate_hz=0.05,
        times=times,
        initial_site=3,
        trap_site=0,
    )
    assert open_result.max_population_closure_error < 1e-10
    assert open_result.sink_population[-1] > 0.0
    assert open_result.loss_population[-1] > 0.0


def test_scientific_validation_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_scientific_validation"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = _profile_config("smoke")
        config["graph_realizations"] = 2
        config["disorder_seeds"] = [3]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["near"]
        config["n_repeats"] = 2
        metrics = run_validation(config, tmp_dir)
        assert metrics["numerics_pass"]
        assert (tmp_dir / "statistical_summary.csv").exists()
        assert (tmp_dir / "group_split_report.json").exists()
        assert (tmp_dir / "classical_control_report.json").exists()
        assert (tmp_dir / "size_generalization_report.json").exists()
        assert (tmp_dir / "scientific_validation_report.md").exists()
        assert (tmp_dir / "figures" / "classification_group_vs_row.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
