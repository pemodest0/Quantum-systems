from __future__ import annotations

import json
from pathlib import Path
import shutil

import networkx as nx
import numpy as np

from oqs_transport import generate_network_instance, graph_from_adjacency
from scripts.run_transport_research_journey_v2 import profile_config, run_journey


def test_fractal_network_families_are_valid() -> None:
    for family in ["sierpinski_gasket", "sierpinski_carpet_like"]:
        instance = generate_network_instance(family, n_sites=13, seed=123)
        assert instance.adjacency.shape == (13, 13)
        assert instance.coordinates.shape == (13, 2)
        assert np.allclose(instance.adjacency, instance.adjacency.T)
        assert np.allclose(np.diag(instance.adjacency), 0.0)
        assert np.all(np.isfinite(instance.coordinates))
        assert nx.is_connected(graph_from_adjacency(instance.adjacency))


def test_research_journey_v2_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_research_journey_v2"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = profile_config("smoke")
        metrics = run_journey(config, tmp_dir)
        assert metrics["numerics_pass"]
        assert metrics["target_record_count"] > 0
        assert metrics["quantum_classical_record_count"] == metrics["target_record_count"]
        assert metrics["fractal_record_count"] > 0
        assert (tmp_dir / "metrics.json").exists()
        assert (tmp_dir / "target_geometry_summary.csv").exists()
        assert (tmp_dir / "quantum_classical_comparison.csv").exists()
        assert (tmp_dir / "fractal_transport_summary.csv").exists()
        assert (tmp_dir / "material_motivation_table.md").exists()
        assert (tmp_dir / "summary.md").exists()
        assert (tmp_dir / "figure_explanations_ptbr.json").exists()
        assert (tmp_dir / "figures" / "target_position_effect_map.png").exists()
        assert (tmp_dir / "figures" / "quantum_vs_classical_delta_map.png").exists()
        assert (tmp_dir / "figures" / "classification_article_panel.png").exists()
        assert (tmp_dir / "figures" / "fractal_msd_and_geometry.png").exists()
        explanations = json.loads((tmp_dir / "figure_explanations_ptbr.json").read_text(encoding="utf-8"))
        assert "target_position_effect_map.png" in explanations
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
