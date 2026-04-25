from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = ROOT / "notebooks"
if str(NOTEBOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(NOTEBOOKS_DIR))

from colab_transport_review import (  # noqa: E402
    current_research_snapshot,
    dephasing_scan,
    make_graph,
    quantum_vs_classical_case,
)


def test_transport_colab_helpers_run_small_cases() -> None:
    graph, pos = make_graph("chain", n=6, seed=3)
    assert graph.number_of_nodes() == 6
    assert len(pos) == 6

    scan, *_ = dephasing_scan("ring", n=6, W=0.3, seed=3, gamma_values=[0.0, 0.1], t_final=4.0, n_times=20)
    assert not scan.empty
    assert {"target_arrival", "von_neumann_entropy", "gamma_phi_over_J"}.issubset(scan.columns)

    merged, summary, *_ = quantum_vs_classical_case("ring", n=6, W=0.3, gamma=0.1, seed=3, t_final=4.0, n_times=20)
    assert not merged.empty
    assert "quantum_minus_classical" in summary


def test_transport_colab_repo_loader_reads_current_outputs() -> None:
    snapshot = current_research_snapshot(ROOT)
    assert "evidence_prep_metrics" in snapshot
    assert "atlas_state" in snapshot
    assert snapshot["evidence_prep_metrics"].get("numerics_pass") is True


def test_transport_colab_notebooks_exist_and_are_valid_json() -> None:
    for name in [
        "colab_transport_tutorial_from_graph_to_lab.ipynb",
        "colab_transport_research_review.ipynb",
    ]:
        path = ROOT / "notebooks" / name
        assert path.exists(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["nbformat"] == 4
        assert len(payload["cells"]) >= 10
