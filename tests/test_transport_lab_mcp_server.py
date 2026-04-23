from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport.mcp_lab_server import READ_ONLY_TOOL_NAMES, TransportLabMcpData  # noqa: E402
from scripts.build_transport_lab_mcp_index import build_index  # noqa: E402


def test_mcp_index_builder_generates_normalized_files() -> None:
    built = build_index()
    expected = {
        "index",
        "campaigns",
        "metric_summaries",
        "entropy_summary",
        "claims",
        "figures",
        "notebooks",
    }
    assert expected.issubset(built.files)
    for key in expected:
        assert built.files[key].exists(), key


def test_mcp_data_status_reads_lab_registry() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    status = data.status()
    assert status["registry_exists"] is True
    assert status["index_exists"] is True
    assert status["data_source"] == "mcp_index"
    assert status["campaign_count"] >= 1
    assert "dynamic_network_atlas" in status["smoke_only_campaigns"]
    assert "list_campaigns" in status["tools"]
    assert "get_lab_status" in status["tools"]


def test_mcp_campaign_listing_includes_evidence_prep() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    campaigns = data.list_campaigns()["campaigns"]
    ids = {row["campaign_id"] for row in campaigns}
    assert "dynamic_network_atlas_evidence_prep" in ids
    assert "paper_reproduction_suite" in ids


def test_mcp_entropy_summary_uses_von_neumann_entropy() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    summary = data.summarize_entropy(campaign_id="dynamic_network_atlas_evidence_prep", top_n=5)
    assert "von Neumann entropy" in summary["meaning"]
    assert "not target arrival" in summary["meaning"]
    assert summary["rows"]
    assert all(row["entropy_mean"] is not None for row in summary["rows"])
    assert all("source_file" in row for row in summary["rows"])


def test_mcp_quantum_classical_summary_adds_verdicts() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    summary = data.quantum_classical_summary(campaign_id="dynamic_network_atlas_evidence_prep", top_n=5)
    assert summary["rows"]
    assert {row["verdict"] for row in summary["rows"]}
    quantum_higher = [row for row in summary["rows"] if row["verdict"] == "quantum_higher"]
    assert all(row["mean"] > 0.05 and row["ci95_low"] > 0 for row in quantum_higher)


def test_mcp_artifact_catalogs_include_colab_notebook_and_figures() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    notebooks = data.list_notebooks()["notebooks"]
    assert any(row["name"] == "colab_open_quantum_transport_lab.ipynb" for row in notebooks)
    figures = data.list_figures(limit=5)
    assert figures["count"] >= len(figures["figures"])


def test_mcp_paper_guardrails_are_available() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    guardrails = data.get_paper_guardrails()
    assert guardrails["paper_reproduction_suite"]
    assert "paper_verdicts" in guardrails["paper_reproduction_suite"]


def test_mcp_campaign_file_reader_is_confined_to_campaign_output() -> None:
    build_index()
    data = TransportLabMcpData.from_root(ROOT)
    ok = data.read_campaign_file("dynamic_network_atlas_evidence_prep", "summary.md", max_chars=2000)
    assert ok["campaign_id"] == "dynamic_network_atlas_evidence_prep"
    blocked = data.read_campaign_file("dynamic_network_atlas_evidence_prep", "..\\..\\pyproject.toml")
    assert "error" in blocked


def test_mcp_tool_manifest_is_read_only() -> None:
    forbidden_fragments = {"run", "simulate", "write", "edit", "delete"}
    assert READ_ONLY_TOOL_NAMES
    for name in READ_ONLY_TOOL_NAMES:
        assert not any(fragment in name for fragment in forbidden_fragments)


def test_mcp_falls_back_to_registry_when_index_is_missing() -> None:
    missing_index = ROOT / "tests" / "_missing_mcp_index_for_fallback"
    data = TransportLabMcpData(root=ROOT, registry_dir=ROOT / "outputs" / "transport_networks" / "lab_registry" / "latest", index_dir=missing_index)
    status = data.status()
    assert status["index_exists"] is False
    assert status["data_source"] == "lab_registry_fallback"
    assert status["fallback_warning"]
    assert data.list_campaigns()["campaigns"]
