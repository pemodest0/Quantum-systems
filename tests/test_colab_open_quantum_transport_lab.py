from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_colab_open_quantum_transport_lab import build  # noqa: E402


def test_colab_open_quantum_transport_lab_builds_clean_english_notebook() -> None:
    payload = build()
    notebook = Path(payload["notebook"])
    assert notebook.exists()

    parsed = json.loads(notebook.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in parsed["cells"])

    assert "Open Quantum Transport on Graphs" in source
    assert "Google Colab" in source
    assert "not a quantum-computer run" in source
    assert "von Neumann entropy" in source
    assert "dynamic_network_atlas_evidence_prep" in source
    assert "quantum_minus_classical" in source
    assert "TCC" not in source
    assert "trabalho de conclus" not in source.lower()


def test_colab_link_points_to_expected_github_colab_route() -> None:
    payload = build()
    assert payload["colab_link"].startswith("https://colab.research.google.com/github/")
    assert payload["colab_link"].endswith("notebooks/colab_open_quantum_transport_lab.ipynb")
