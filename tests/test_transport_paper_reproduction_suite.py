from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np

from oqs_transport import (
    chain_adjacency,
    count_resolved_local_peaks,
    disorder_localization_score,
    estimate_msd_exponent,
    solve_effective_source_drain_steady_state,
)
from scripts.run_transport_paper_reproduction_suite import profile_config, run_suite


EXPECTED_PAPERS = {
    "muelken_blumen_2011",
    "razzoli_2021",
    "plenio_huelga_2008",
    "mohseni_2008",
    "rebentrost_2009",
    "whitfield_2010",
    "rossi_2015",
    "minello_2019",
    "novo_2016",
    "maier_2019",
    "caruso_2009",
    "kendon_2007",
    "coates_2023",
    "blach_2025",
    "rojo_francas_2024",
    "anderson_1958",
    "walschaers_2016",
    "manzano_2013",
    "coutinho_2022",
    "gamble_2010",
    "engel_2007",
}


def test_paper_reproduction_suite_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_paper_reproduction_suite"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        config = profile_config("smoke")
        config["graph_realizations"] = 2
        config["deterministic_graph_realizations"] = 2
        config["disorder_seeds"] = [3]
        config["dephasing_over_coupling"] = [0.0, 0.2]
        config["target_styles"] = ["near"]
        config["n_repeats"] = 2
        metrics = run_suite(config, tmp_dir)
        assert metrics["numerics_pass"]
        assert metrics["paper_claim_count"] >= len(EXPECTED_PAPERS)
        assert (tmp_dir / "paper_claims.json").exists()
        assert (tmp_dir / "paper_verdicts.json").exists()
        assert (tmp_dir / "paper_reproduction_table.csv").exists()
        assert (tmp_dir / "paper_reproduction_report.md").exists()
        assert (tmp_dir / "gamma_resolved_curves.csv").exists()
        assert (tmp_dir / "fractal_paper_benchmark.csv").exists()
        assert (tmp_dir / "localization_disorder_benchmark.csv").exists()
        assert (tmp_dir / "steady_state_transport_benchmark.csv").exists()
        assert (tmp_dir / "noisy_network_benchmark.csv").exists()
        assert (tmp_dir / "figures" / "paper_verdict_overview.png").exists()
        assert (tmp_dir / "figures" / "paper_claim_confidence.png").exists()

        claims = json.loads((tmp_dir / "paper_claims.json").read_text(encoding="utf-8"))
        verdicts = json.loads((tmp_dir / "paper_verdicts.json").read_text(encoding="utf-8"))
        assert EXPECTED_PAPERS.issubset(set(verdicts))
        assert all(item["claim_id"] for item in claims)
        assert all(item["paper_key"] in EXPECTED_PAPERS for item in claims)
        assert all(item["threshold"] != "" for item in claims)
        assert all(item["observed_metric"] for item in claims)
        assert all(item["reason"] for item in claims)
        assert all(item["reason"] and item["threshold"] != "" for item in claims if item["verdict"] == "matched")
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_paper_profile_maps_to_broad_validation_settings() -> None:
    config = profile_config("paper")
    assert config["profile"] == "paper"
    assert "chain" in config["families"]
    assert "random_geometric" in config["families"]
    assert "exponential_distance" in config["edge_models_sensitivity"]


def test_confirm_profile_is_focused_on_current_strong_candidate() -> None:
    config = profile_config("confirm")
    assert config["profile"] == "confirm"
    assert config["families"] == ["modular_two_community"]
    assert config["edge_models_main"] == ["unweighted"]
    assert config["target_styles"] == ["near"]
    assert max(config["dephasing_over_coupling"]) >= 0.8


def test_gamma_peak_detector_identifies_zero_one_and_two_peaks() -> None:
    monotonic = [{"g": i, "a": value} for i, value in enumerate([0.1, 0.2, 0.3, 0.4])]
    one_peak = [{"g": i, "a": value} for i, value in enumerate([0.1, 0.4, 0.2, 0.1])]
    two_peaks = [{"g": i, "a": value} for i, value in enumerate([0.1, 0.5, 0.1, 0.12, 0.46, 0.11])]
    assert count_resolved_local_peaks(monotonic, x_key="g", y_key="a") == 0
    assert count_resolved_local_peaks(one_peak, x_key="g", y_key="a") == 1
    assert count_resolved_local_peaks(two_peaks, x_key="g", y_key="a") == 2


def test_msd_exponent_fit_and_rejection() -> None:
    exponent = estimate_msd_exponent([1, 2, 4, 8, 16], [1, 4, 16, 64, 256])
    assert exponent is not None
    assert abs(exponent - 2.0) < 1e-9
    assert estimate_msd_exponent([0, 1], [0, 1]) is None


def test_anderson_localization_score_synthetic_case() -> None:
    rows = [
        {"family": "chain", "disorder_strength_over_coupling": 0.0, "participation_ratio": 5.0, "ipr": 0.2, "msd": 4.0},
        {"family": "chain", "disorder_strength_over_coupling": 2.0, "participation_ratio": 2.0, "ipr": 0.6, "msd": 1.0},
        {"family": "ring", "disorder_strength_over_coupling": 0.0, "participation_ratio": 6.0, "ipr": 0.16, "msd": 5.0},
        {"family": "ring", "disorder_strength_over_coupling": 2.0, "participation_ratio": 3.0, "ipr": 0.4, "msd": 2.0},
    ]
    summary = disorder_localization_score(rows)
    assert summary["matched_family_count"] == 2


def test_effective_source_drain_steady_state_is_valid() -> None:
    result = solve_effective_source_drain_steady_state(
        chain_adjacency(4),
        source_site=3,
        drain_site=0,
        coupling_hz=1.0,
        dephasing_rate_hz=0.1,
        reset_rate_hz=0.5,
        site_energies_hz=np.zeros(4),
    )
    assert result["current"] > 0.0
    assert result["trace_error"] < 1e-8
    assert result["min_eigenvalue"] > -1e-7
    assert result["residual_norm"] < 1e-6
