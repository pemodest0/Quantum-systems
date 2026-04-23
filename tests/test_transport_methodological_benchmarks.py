from __future__ import annotations

from pathlib import Path
import shutil

from scripts.run_transport_methodological_benchmarks import _profile_config, run_benchmarks


def test_methodological_benchmarks_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_methodological_benchmarks"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = _profile_config("smoke")
        config["families"] = ["chain", "ring"]
        config["n_sites_values"] = [5]
        config["edge_models_main"] = ["unweighted"]
        config["edge_models_sensitivity"] = ["unweighted"]
        config["disorder_seeds"] = [3]
        config["disorder_strength_over_coupling"] = [0.0]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["far"]
        config["t_final_closed"] = 3.0
        config["t_final_open"] = 4.0
        config["n_time_samples"] = 28
        metrics = run_benchmarks(config, tmp_dir)
        assert metrics["open_signature_count"] == 2
        assert metrics["acceptance"]["numerics_pass"]
        assert (tmp_dir / "methodology.md").exists()
        assert (tmp_dir / "summary.md").exists()
        assert (tmp_dir / "literature_guardrails.json").exists()
        assert (tmp_dir / "plain_ptbr_explanations.json").exists()
        assert (tmp_dir / "figures" / "closed_walk_return_probability.png").exists()
        assert (tmp_dir / "figures" / "classification_controls.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
