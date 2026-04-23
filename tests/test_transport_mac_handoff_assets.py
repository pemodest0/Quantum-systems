from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mac_handoff_docs_and_scripts_exist() -> None:
    paths = [
        ROOT / "AGENTS.md",
        ROOT / "docs" / "handoffs" / "workspace_repo_map.md",
        ROOT / "docs" / "handoffs" / "transport_lab_mac_handoff.md",
        ROOT / "docs" / "handoffs" / "transport_research_scope_ptbr.md",
        ROOT / "docs" / "handoffs" / "transport_professor_conversation_ptbr.md",
        ROOT / "scripts" / "mac_transport_bootstrap.sh",
        ROOT / "scripts" / "mac_transport_long_run.sh",
    ]
    for path in paths:
        assert path.exists(), f"missing expected handoff asset: {path}"


def test_agents_points_to_mac_handoff_assets() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/handoffs/transport_lab_mac_handoff.md" in text
    assert "docs/handoffs/workspace_repo_map.md" in text
    assert "docs/handoffs/transport_research_scope_ptbr.md" in text
    assert "docs/handoffs/transport_professor_conversation_ptbr.md" in text
    assert "scripts/mac_transport_bootstrap.sh" in text
    assert "scripts/mac_transport_long_run.sh" in text
