from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_transport_lab_master_pipeline import (  # noqa: E402
    REGISTRY_DIR,
    build_campaign_manifest,
    build_claims_and_critic,
    build_master_results,
    build_registry_outputs,
    build_uncertainty,
)


def test_master_manifest_finds_expected_campaigns() -> None:
    manifest = build_campaign_manifest()
    ids = {entry["campaign_id"] for entry in manifest}
    assert "research_journey_v2" in ids
    assert "paper_reproduction_suite" in ids
    assert "dynamic_network_atlas" in ids
    assert "dynamic_network_atlas_evidence_prep" in ids
    assert "dynamic_network_atlas_intense" in ids
    atlas = next(entry for entry in manifest if entry["campaign_id"] == "dynamic_network_atlas")
    assert atlas["evidence_status"] in {"smoke_only", "scientific_candidate", "exploratory_interactive", "unknown"}
    prep = next(entry for entry in manifest if entry["campaign_id"] == "dynamic_network_atlas_evidence_prep")
    assert prep["evidence_status"] != "smoke_only"
    intense = next(entry for entry in manifest if entry["campaign_id"] == "dynamic_network_atlas_intense")
    assert intense["script"].endswith("--profile intense")


def test_master_results_keep_audit_columns_and_uncertainty_is_finite() -> None:
    manifest = build_campaign_manifest()
    rows = build_master_results(manifest)
    assert rows
    sample = rows[0]
    for key in ["campaign_id", "source_file", "family", "n_sites", "instance_id", "disorder_seed", "target_style", "trap_site"]:
        assert key in sample
    uncertainty = build_uncertainty(rows)
    assert uncertainty
    finite_rows = [row for row in uncertainty if int(row.get("arrival_n", 0)) > 0]
    assert finite_rows
    assert all("arrival_ci95_low" in row and "arrival_ci95_high" in row for row in finite_rows)


def test_master_critic_blocks_smoke_and_weak_quantum_claims() -> None:
    manifest = [
        {
            "campaign_id": "dynamic_network_atlas",
            "evidence_status": "smoke_only",
            "profile": "smoke",
            "numerics_pass": True,
        }
    ]
    uncertainty = [
        {
            "group_level": "campaign_family",
            "campaign_id": "dynamic_network_atlas",
            "family": "chain",
            "arrival_n": 4,
            "arrival_mean": 0.2,
            "arrival_ci95_low": 0.1,
            "arrival_ci95_high": 0.3,
            "quantum_minus_classical_n": 4,
            "quantum_minus_classical_mean": 0.08,
            "quantum_minus_classical_ci95_low": 0.02,
            "gain_n": 4,
            "gain_mean": 0.08,
            "gain_ci95_low": 0.02,
        }
    ]
    claims, text = build_claims_and_critic(manifest, uncertainty)
    blocked = " ".join(item["claim"] for item in claims["blocked_claims"])
    assert "dynamic_network_atlas is scientifically conclusive" in blocked
    assert "smoke" in text.lower()


def test_master_registry_outputs_are_generated() -> None:
    if REGISTRY_DIR.exists():
        shutil.rmtree(REGISTRY_DIR)
    metrics = build_registry_outputs()
    assert metrics["campaign_count"] >= 7
    assert metrics["master_result_count"] > 0
    assert (REGISTRY_DIR / "campaign_manifest.json").exists()
    assert (REGISTRY_DIR / "master_results.csv").exists()
    assert (REGISTRY_DIR / "master_uncertainty.csv").exists()
    assert (REGISTRY_DIR / "master_claims.json").exists()
    assert (REGISTRY_DIR / "master_critic_report.md").exists()
    assert (REGISTRY_DIR / "transport_lab_memory.md").exists()
    assert (REGISTRY_DIR / "figures" / "uncertainty_dashboard.png").exists()
    assert (REGISTRY_DIR / "figures" / "evidence_prep_decision_panel.png").exists()
    assert (ROOT / "notebooks" / "transport_lab_master_notebook.ipynb").exists()
    assert (ROOT / "outputs" / "transport_networks" / "master_scientific_report" / "latest" / "master_report.md").exists()
    with (REGISTRY_DIR / "master_results.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    claims = json.loads((REGISTRY_DIR / "master_claims.json").read_text(encoding="utf-8"))
    assert "allowed_claims" in claims
    assert "blocked_claims" in claims
