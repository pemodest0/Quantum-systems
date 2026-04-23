from __future__ import annotations

from pathlib import Path
import shutil

from oqs_transport.campaign_helpers import write_summary_markdown
from scripts.run_transport_2d_target_position_campaign import build_2d_target_position_config
from scripts.run_transport_material_full_campaign import build_material_full_config
from scripts.run_transport_material_long_range_campaign import build_material_long_range_config
from scripts.run_transport_ring_ceiling_campaign import build_ring_ceiling_config
from scripts.run_transport_ring_size_campaign import build_ring_size_config
from scripts.run_transport_ring_target_sweep_campaign import build_ring_target_sweep_config
from scripts.run_transport_strong_disorder_robustness_campaign import build_strong_disorder_robustness_config


def test_ring_ceiling_config_shape() -> None:
    config = build_ring_ceiling_config()
    assert len(config["scenarios"]) == 2
    assert config["sweep"]["dephasing_over_coupling"][-1] == 1.6


def test_ring_size_config_has_all_sizes() -> None:
    config = build_ring_size_config()
    scenario_names = [block["name"] for block in config["scenarios"]]
    assert len(config["scenarios"]) == 8
    for size in [6, 8, 10, 12]:
        assert any(f"N{size}" in name for name in scenario_names)


def test_target_position_configs_cover_requested_targets() -> None:
    ring_config = build_ring_target_sweep_config()
    lattice_config = build_2d_target_position_config()
    ring_targets = sorted(block["trap_site"] for block in ring_config["scenarios"])
    lattice_targets = sorted(block["trap_site"] for block in lattice_config["scenarios"])
    assert ring_targets == [0, 1, 2, 3]
    assert lattice_targets == [0, 3, 5, 10]


def test_robustness_and_material_configs_have_expected_scenario_counts() -> None:
    assert len(build_strong_disorder_robustness_config()["scenarios"]) == 3
    assert len(build_material_full_config()["scenarios"]) == 5


def test_material_long_range_config_selects_two_winners() -> None:
    base_results = {
        "scenarios": [
            {"scenario_name": "A", "efficiency_mean": [[0.4, 0.5], [0.45, 0.55]], "efficiency_std": [[0.01, 0.01], [0.01, 0.01]], "disorder_strength_over_coupling": [0.0, 0.4], "dephasing_over_coupling": [0.0, 0.2]},
            {"scenario_name": "B", "efficiency_mean": [[0.5, 0.6], [0.55, 0.65]], "efficiency_std": [[0.01, 0.01], [0.01, 0.01]], "disorder_strength_over_coupling": [0.0, 0.4], "dephasing_over_coupling": [0.0, 0.2]},
            {"scenario_name": "C", "efficiency_mean": [[0.45, 0.47], [0.46, 0.48]], "efficiency_std": [[0.01, 0.01], [0.01, 0.01]], "disorder_strength_over_coupling": [0.0, 0.4], "dephasing_over_coupling": [0.0, 0.2]},
        ]
    }
    base_config = {
        "scenarios": [
            {"name": "A", "medium": {"medium_type": "chain_1d", "n_sites": 6}, "coupling_hz": 1.0, "sink_rate_hz": 0.65, "loss_rate_hz": 0.02, "initial_site": 5, "trap_site": 0},
            {"name": "B", "medium": {"medium_type": "ring", "n_sites": 6}, "coupling_hz": 1.0, "sink_rate_hz": 0.65, "loss_rate_hz": 0.02, "initial_site": 3, "trap_site": 0},
            {"name": "C", "medium": {"medium_type": "square_lattice_2d", "n_rows": 2, "n_cols": 2}, "coupling_hz": 1.0, "sink_rate_hz": 0.65, "loss_rate_hz": 0.02, "initial_site": 3, "trap_site": 0},
        ]
    }
    config = build_material_long_range_config(base_results, base_config)
    assert len(config["scenarios"]) == 4


def test_summary_markdown_contains_guardrail_sections() -> None:
    tmp_dir = Path("tests") / "_tmp_summary_guardrail"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    try:
        output_path = tmp_dir / "summary.md"
        write_summary_markdown(
            output_path,
            title="Smoke Summary",
            literature_guardrails=[{"key": "RefA", "url": "https://example.com", "reading": "Reference text"}],
            overview_lines=["Overview"],
            measured_lines=["Measured"],
            agreement_lines=["Agreement"],
            uncertainty_lines=["Uncertainty"],
            table_headers=["a", "b"],
            table_rows=[["1", "2"]],
        )
        text = output_path.read_text(encoding="utf-8")
        assert "## Literature guardrails" in text
        assert "## What was measured" in text
        assert "## What is still not proven" in text
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
