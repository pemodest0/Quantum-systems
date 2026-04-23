from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_physics_curriculum_has_required_modules() -> None:
    curriculum_dir = ROOT / "docs" / "physics_curriculum"
    required = {
        "quantum_states_and_density_matrices.md",
        "tight_binding_and_graphs.md",
        "open_quantum_systems_lindblad.md",
        "dephasing_loss_sink.md",
        "entropy_purity_ipr.md",
        "quantum_transport_observables.md",
        "environment_assisted_transport.md",
        "how_to_read_lab_figures.md",
        "stat_mech_for_open_systems.md",
        "numerical_methods_and_validation.md",
    }
    existing = {path.name for path in curriculum_dir.glob("*.md")}
    assert required <= existing


def test_transport_paper_cards_are_present_and_source_backed() -> None:
    paper_dir = ROOT / "docs" / "papers" / "transport"
    cards = sorted(paper_dir.glob("*.md"))
    assert len(cards) >= 10
    for card in cards:
        text = card.read_text(encoding="utf-8")
        assert "## Source" in text
        assert "DOI:" in text
        assert "## Limitations" in text
        assert "## Relation with our lab" in text


def test_exercise_bank_has_required_categories_and_counts() -> None:
    bank_path = ROOT / "docs" / "physics_exercises" / "transport_exercise_bank.json"
    payload = json.loads(bank_path.read_text(encoding="utf-8"))
    exercises = payload["exercises"]
    assert len(exercises) >= 70
    counts: dict[str, int] = {}
    for exercise in exercises:
        counts[str(exercise["category"])] = counts.get(str(exercise["category"]), 0) + 1
        assert exercise["question"]
        assert exercise["expected_answer"]
        assert exercise["common_mistake"]
        assert exercise["grading_criteria"]
    assert counts["conceptual"] >= 20
    assert counts["figure_reading"] >= 20
    assert counts["transport_lindblad"] >= 20
    assert counts["trap"] >= 10

