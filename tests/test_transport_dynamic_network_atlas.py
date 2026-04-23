from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_transport_dynamic_network_atlas import profile_config, run_atlas


def test_dynamic_network_atlas_evidence_prep_profile_is_non_smoke() -> None:
    config = profile_config("evidence_prep")
    assert config["profile"] == "evidence_prep"
    assert config["families"] == [
        "chain",
        "ring",
        "bottleneck",
        "clustered",
        "random_geometric",
        "modular_two_community",
        "square_lattice_2d",
    ]
    assert config["n_sites_values"] == [8, 12]
    assert len(config["disorder_seeds"]) == 6
    assert 0.0 in config["dephasing_over_coupling"]
    assert config["target_styles"] == ["near", "far"]


def test_dynamic_network_atlas_intense_profile_is_heavier_than_strong() -> None:
    strong = profile_config("strong")
    intense = profile_config("intense")
    assert intense["profile"] == "intense"
    assert set(intense["families"]) == set(strong["families"])
    assert len(intense["n_sites_values"]) > len(strong["n_sites_values"])
    assert len(intense["disorder_seeds"]) > len(strong["disorder_seeds"])
    assert len(intense["dephasing_over_coupling"]) > len(strong["dephasing_over_coupling"])
    assert intense["checkpoint_every"] < strong["checkpoint_every"]


def test_dynamic_network_atlas_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_dynamic_network_atlas"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = profile_config("smoke")
        config["families"] = ["chain", "ring", "random_geometric"]
        config["n_sites_values"] = [6]
        config["disorder_seeds"] = [3]
        config["disorder_strength_over_coupling"] = [0.0]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["far"]
        config["t_final"] = 3.5
        config["n_time_samples"] = 28

        metrics = run_atlas(config, tmp_dir)

        assert metrics["numerics_pass"]
        assert metrics["record_count"] == 3
        assert (tmp_dir / "atlas_records.csv").exists()
        assert (tmp_dir / "atlas_summary_by_family.csv").exists()
        assert (tmp_dir / "atlas_summary_by_target.csv").exists()
        assert (tmp_dir / "atlas_regime_fractions.csv").exists()
        assert (tmp_dir / "quantum_classical_delta.csv").exists()
        assert (tmp_dir / "atlas_metrics.json").exists()
        assert (tmp_dir / "config_used.json").exists()
        assert (tmp_dir / "run_metadata.json").exists()
        assert (tmp_dir / "summary.md").exists()
        assert (tmp_dir / "figure_explanations_ptbr.json").exists()
        assert (tmp_dir / "figures" / "atlas_dashboard.png").exists()
        assert (tmp_dir / "figures" / "arrival_by_family_heatmap.png").exists()
        assert (tmp_dir / "figures" / "entropy_coherence_panel.png").exists()
        assert (tmp_dir / "figures" / "quantum_minus_classical_map.png").exists()
        assert (tmp_dir / "figures" / "regime_phase_map.png").exists()
        assert (tmp_dir / "figures" / "signature_embedding.png").exists()
        assert (tmp_dir / "figures" / "family_fingerprint_radar.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_dynamic_network_atlas_records_have_required_signatures() -> None:
    tmp_dir = Path("tests") / "_tmp_dynamic_network_atlas_fields"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = profile_config("smoke")
        config["families"] = ["chain"]
        config["n_sites_values"] = [6]
        config["disorder_seeds"] = [3]
        config["disorder_strength_over_coupling"] = [0.0]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["far"]
        config["t_final"] = 3.5
        config["n_time_samples"] = 28

        run_atlas(config, tmp_dir)
        text = (tmp_dir / "atlas_records.csv").read_text(encoding="utf-8").splitlines()
        header = text[0].split(",")
        row = dict(zip(header, text[1].split(","), strict=False))
        required = [
            "best_arrival",
            "best_sink_hitting_time_filled",
            "best_mean_coherence_l1",
            "best_final_entropy",
            "best_final_purity",
            "best_population_shannon_entropy",
            "best_participation_ratio",
            "best_ipr",
            "best_final_msd",
            "best_final_front_width",
            "classical_arrival",
            "quantum_minus_classical",
            "regime_label",
            "regime_confidence",
        ]
        for key in required:
            assert key in row
        numeric = [float(row[key]) for key in required if key not in {"regime_label"}]
        assert all(np.isfinite(value) for value in numeric)
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_dynamic_network_atlas_notebook_is_static_and_points_to_latest() -> None:
    notebook = Path("notebooks") / "dynamic_network_atlas.ipynb"
    payload = json.loads(notebook.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])
    assert "dynamic_network_atlas" in source
    assert "RUN_NOW = False" in source
    assert "outputs' / 'transport_networks' / 'dynamic_network_atlas' / 'latest" in source
