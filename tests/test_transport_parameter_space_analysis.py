from __future__ import annotations

import csv

from scripts.analyze_transport_parameter_space import run_analysis


def _read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_parameter_space_analysis_outputs(tmp_path) -> None:
    payload = run_analysis(tmp_path)
    assert payload["summary"]
    assert (tmp_path / "parameter_cost_summary.csv").exists()
    assert (tmp_path / "family_cost_breakdown.csv").exists()
    assert (tmp_path / "combinatorial_factors.csv").exists()
    assert (tmp_path / "auxiliary_benchmark_costs.csv").exists()
    assert (tmp_path / "parameter_space_report.md").exists()
    assert (tmp_path / "figures" / "combinatorial_explosion_dashboard.png").exists()

    summary = _read_rows(tmp_path / "parameter_cost_summary.csv")
    by_key = {(row["campaign"], row["profile"]): row for row in summary}
    assert int(float(by_key[("dynamic_network_atlas", "strong")]["quantum_simulations"])) == 400000
    assert int(float(by_key[("dynamic_network_atlas", "intense")]["quantum_simulations"])) == 3263040
    assert int(float(by_key[("dynamic_network_atlas", "evidence_prep")]["quantum_simulations"])) == 7224
    assert int(float(by_key[("paper_reproduction_suite_validation", "paper")]["quantum_simulations"])) == 3240
