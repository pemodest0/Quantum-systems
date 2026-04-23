from __future__ import annotations

import csv
from pathlib import Path
import shutil

from scripts.build_transport_network_classification_pack import build_pack
from scripts.run_transport_modular_refinement_campaign import profile_config, run_campaign


def test_modular_refinement_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_modular_refinement"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = profile_config("smoke")
        metrics = run_campaign(config, tmp_dir)
        assert metrics["numerics_pass"]
        assert metrics["curve_record_count"] > 0
        assert (tmp_dir / "gamma_curve_records.csv").exists()
        assert (tmp_dir / "gamma_curve_statistics.csv").exists()
        assert (tmp_dir / "peak_diagnostics.json").exists()
        assert (tmp_dir / "summary.md").exists()
        assert (tmp_dir / "figures" / "arrival_vs_phase_scrambling_curves.png").exists()
        assert (tmp_dir / "figures" / "gain_w_gamma_heatmap.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_network_classification_pack_from_synthetic_records() -> None:
    tmp_root = Path("tests") / "_tmp_network_classification_pack"
    source = tmp_root / "source"
    output = tmp_root / "output"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    try:
        source.mkdir(parents=True)
        rows = []
        for family, offset in [("alpha", 0.0), ("beta", 10.0)]:
            for n_sites in [8, 10]:
                for group in range(4):
                    for repeat in range(2):
                        rows.append(
                            {
                                "record_id": f"{family}_{n_sites}_{group}_{repeat}",
                                "family": family,
                                "n_sites": n_sites,
                                "graph_seed": group,
                                "validation_group_id": f"{family}_N{n_sites}_g{group}",
                                "zero_dephasing_arrival": offset + group * 0.1,
                                "best_arrival": offset + 1.0 + group * 0.1,
                                "dephasing_gain": 1.0,
                                "best_dephasing_over_coupling": 0.8,
                                "classical_arrival": offset + 0.2,
                                "classical_sink_hitting_time_filled": 1.0 + offset,
                                "classical_loss_population": 0.1,
                                "classical_network_population": 0.2,
                                "arrival_quantum_minus_classical": 0.8,
                                "hitting_time_quantum_minus_classical": 0.1,
                                "loss_quantum_minus_classical": 0.0,
                                "topology_mean_degree": offset + 2.0,
                                "topology_spectral_radius": offset + 3.0,
                            }
                        )
        with (source / "dynamic_signatures_with_classical.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        metrics = build_pack(source, output, n_repeats=2)
        assert metrics["record_count"] == len(rows)
        assert metrics["combined_accuracy"] >= metrics["combined_baseline"]
        assert (output / "classification_reports.json").exists()
        assert (output / "size_generalization_report.json").exists()
        assert (output / "figures" / "accuracy_by_feature_set.png").exists()
        assert (output / "figures" / "combined_confusion_matrix.png").exists()
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
