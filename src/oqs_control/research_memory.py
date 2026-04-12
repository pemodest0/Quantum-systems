from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class ResearchMemoryRecord:
    record_id: str
    kind: str
    source_id: str
    source_dir: str
    captured_at_utc: str
    status: str
    summary: dict[str, Any]
    artifacts: tuple[ArtifactRecord, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_record(path: Path, root: Path) -> ArtifactRecord:
    return ArtifactRecord(
        path=str(path.relative_to(root)),
        sha256=sha256_file(path),
        bytes=int(path.stat().st_size),
    )


def collect_artifacts(source_dir: Path, root: Path) -> tuple[ArtifactRecord, ...]:
    patterns = ("*.json", "*.md", "*.png")
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(source_dir.rglob(pattern))
    return tuple(artifact_record(path, root) for path in sorted(paths))


def compact_reproduction_summary(metrics: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in ("paper_id", "workflow_id", "status", "benchmark_type", "comparison_type"):
        if key in metrics:
            payload[key] = metrics[key]
    if "summary" in results:
        payload["runner_summary"] = results["summary"]
    for key in (
        "best_fit",
        "fidelity_summary",
        "noiseless_reconstruction",
        "failure_metrics",
        "hilbert_vs_liouville",
        "optimization",
        "robustness_grid",
        "target_operation",
        "target_state",
        "analytical_population_averaging",
        "grape_preparation",
        "error_summary",
        "physicality_summary",
        "prediction_summary",
        "fit_summary",
        "memory_witness",
        "control_summary",
        "sequence_table",
        "reconstruction_summary",
        "spectroscopy_summary",
        "state_preparation_summary",
        "decision_summary",
        "lab_comparison",
    ):
        if key in metrics:
            payload[key] = metrics[key]
    return payload


def collect_reproduction_records(root: Path) -> list[ResearchMemoryRecord]:
    outputs = root / "outputs" / "repro"
    records: list[ResearchMemoryRecord] = []
    if not outputs.exists():
        return records

    captured_at = datetime.now(timezone.utc).isoformat()
    for latest_dir in sorted(outputs.glob("*/latest")):
        source_id = latest_dir.parent.name
        metrics = read_json_if_exists(latest_dir / "metrics.json")
        results = read_json_if_exists(latest_dir / "results.json")
        run_metadata = read_json_if_exists(latest_dir / "run_metadata.json")
        record_hash_input = json.dumps(
            {
                "source_id": source_id,
                "metrics_sha256": run_metadata.get("metrics_sha256"),
                "config_used_sha256": run_metadata.get("config_used_sha256"),
                "results_sha256": run_metadata.get("results_sha256"),
            },
            sort_keys=True,
        ).encode("utf-8")
        record_id = hashlib.sha256(record_hash_input).hexdigest()[:16]
        records.append(
            ResearchMemoryRecord(
                record_id=record_id,
                kind="reproduction",
                source_id=source_id,
                source_dir=str(latest_dir.relative_to(root)),
                captured_at_utc=captured_at,
                status=str(metrics.get("status", "unknown")),
                summary=compact_reproduction_summary(metrics, results),
                artifacts=collect_artifacts(latest_dir, root),
            )
        )
    return records


def collect_workflow_records(root: Path) -> list[ResearchMemoryRecord]:
    outputs = root / "outputs" / "workflows"
    records: list[ResearchMemoryRecord] = []
    if not outputs.exists():
        return records

    captured_at = datetime.now(timezone.utc).isoformat()
    for latest_dir in sorted(outputs.glob("*/latest")):
        source_id = latest_dir.parent.name
        metrics = read_json_if_exists(latest_dir / "metrics.json")
        results = read_json_if_exists(latest_dir / "results.json")
        run_metadata = read_json_if_exists(latest_dir / "run_metadata.json")
        record_hash_input = json.dumps(
            {
                "source_id": source_id,
                "metrics_sha256": run_metadata.get("metrics_sha256"),
                "config_used_sha256": run_metadata.get("config_used_sha256"),
                "results_sha256": run_metadata.get("results_sha256"),
            },
            sort_keys=True,
        ).encode("utf-8")
        record_id = hashlib.sha256(record_hash_input).hexdigest()[:16]
        records.append(
            ResearchMemoryRecord(
                record_id=record_id,
                kind="workflow",
                source_id=source_id,
                source_dir=str(latest_dir.relative_to(root)),
                captured_at_utc=captured_at,
                status=str(metrics.get("status", "unknown")),
                summary=compact_reproduction_summary(metrics, results),
                artifacts=collect_artifacts(latest_dir, root),
            )
        )
    return records


def write_jsonl(path: Path, records: list[ResearchMemoryRecord]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_index(path: Path, records: list[ResearchMemoryRecord]) -> None:
    index = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": [
            {
                "record_id": record.record_id,
                "kind": record.kind,
                "source_id": record.source_id,
                "status": record.status,
                "source_dir": record.source_dir,
                "artifact_count": len(record.artifacts),
            }
            for record in records
        ],
    }
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown_summary(path: Path, records: list[ResearchMemoryRecord]) -> None:
    lines = [
        "# Collaborative Research Memory",
        "",
        "This file is generated by `scripts/research_memory_agent.py`.",
        "",
        "It stores reproducible simulation, paper-reproduction, and future lab-data",
        "records in a compact local memory so collaborators can audit what has been",
        "run and which artifacts support each claim.",
        "",
        f"Record count: `{len(records)}`",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record.source_id}",
                "",
                f"- Record ID: `{record.record_id}`",
                f"- Kind: `{record.kind}`",
                f"- Status: `{record.status}`",
                f"- Source directory: `{record.source_dir}`",
                f"- Artifact count: `{len(record.artifacts)}`",
                "",
                "Summary:",
                "",
                "```json",
                json.dumps(record.summary, indent=2, ensure_ascii=False),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_research_memory(root: Path, output_dir: Path | None = None) -> list[ResearchMemoryRecord]:
    active_output = output_dir or (root / "lab" / "research_memory")
    active_output.mkdir(parents=True, exist_ok=True)
    records = collect_reproduction_records(root)
    records.extend(collect_workflow_records(root))
    write_jsonl(active_output / "records.jsonl", records)
    write_index(active_output / "index.json", records)
    write_markdown_summary(active_output / "SUMMARY.md", records)
    return records
