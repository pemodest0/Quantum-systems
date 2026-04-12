from __future__ import annotations

import json
from pathlib import Path
import shutil

from oqs_control.research_memory import build_research_memory


def test_research_memory_collects_minimal_repro_record() -> None:
    root = Path("tests") / "_tmp_research_memory"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    latest = root / "outputs" / "repro" / "demo_paper" / "latest"
    latest.mkdir(parents=True)
    (latest / "metrics.json").write_text(
        json.dumps({"paper_id": "demo_paper", "status": "completed", "best_fit": {"rmse": 0.1}}),
        encoding="utf-8",
    )
    (latest / "results.json").write_text(
        json.dumps({"summary": {"rmse": 0.1}}),
        encoding="utf-8",
    )
    (latest / "config_used.json").write_text(json.dumps({"demo": True}), encoding="utf-8")

    output_dir = root / "lab" / "research_memory"
    records = build_research_memory(root, output_dir)

    assert len(records) == 1
    assert records[0].source_id == "demo_paper"
    assert records[0].status == "completed"
    assert (output_dir / "records.jsonl").exists()
    assert (output_dir / "index.json").exists()
    assert (output_dir / "SUMMARY.md").exists()
    shutil.rmtree(root)


def test_research_memory_collects_workflow_record() -> None:
    root = Path("tests") / "_tmp_research_memory_workflow"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    latest = root / "outputs" / "workflows" / "demo_workflow" / "latest"
    latest.mkdir(parents=True)
    (latest / "metrics.json").write_text(
        json.dumps(
            {
                "workflow_id": "demo_workflow",
                "status": "completed",
                "decision_summary": {"selected_sequence": "CPMG-8"},
            }
        ),
        encoding="utf-8",
    )
    (latest / "results.json").write_text(
        json.dumps({"summary": {"selected_sequence": "CPMG-8"}}),
        encoding="utf-8",
    )
    (latest / "config_used.json").write_text(json.dumps({"demo": True}), encoding="utf-8")

    output_dir = root / "lab" / "research_memory"
    records = build_research_memory(root, output_dir)

    assert len(records) == 1
    assert records[0].kind == "workflow"
    assert records[0].source_id == "demo_workflow"
    assert records[0].summary["decision_summary"]["selected_sequence"] == "CPMG-8"
    shutil.rmtree(root)
