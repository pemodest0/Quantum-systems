from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "outputs" / "transport_networks" / "lab_registry" / "latest"
INDEX_DIR = ROOT / "outputs" / "transport_networks" / "mcp_index" / "latest"

METRICS = [
    "arrival",
    "gain",
    "entropy",
    "purity",
    "shannon_entropy",
    "coherence",
    "participation_ratio",
    "ipr",
    "msd",
    "front_width",
    "quantum_minus_classical",
    "classical_arrival",
    "sink_hitting_time",
]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    return int(numeric) if numeric is not None else None


def _maybe_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _campaign_id_from_path(path: Path, campaigns: list[dict[str, Any]]) -> str | None:
    resolved = path.resolve()
    for campaign in campaigns:
        output_dir = Path(str(campaign.get("output_dir", ""))).resolve()
        if output_dir and output_dir in [resolved, *resolved.parents]:
            return str(campaign.get("campaign_id"))
    return None


def _verdict_for_quantum_classical(mean: float | None, ci_low: float | None, ci_high: float | None) -> str:
    if mean is None or ci_low is None or ci_high is None:
        return "inconclusive"
    if mean > 0.05 and ci_low > 0:
        return "quantum_higher"
    if mean < -0.05 and ci_high < 0:
        return "classical_higher"
    if abs(mean) < 0.05 or ci_low <= 0 <= ci_high:
        return "classical_explains_or_inconclusive"
    return "inconclusive"


@dataclass(frozen=True)
class BuiltMcpIndex:
    output_dir: Path
    files: dict[str, Path]

    def to_dict(self) -> dict[str, str]:
        return {name: str(path) for name, path in self.files.items()}


def load_campaigns() -> list[dict[str, Any]]:
    campaigns = _read_json(REGISTRY_DIR / "campaign_manifest.json", [])
    if not isinstance(campaigns, list):
        return []
    normalized = []
    for row in campaigns:
        normalized.append(
            {
                "campaign_id": row.get("campaign_id"),
                "script": row.get("script"),
                "profile": row.get("profile"),
                "status": row.get("status"),
                "evidence_status": row.get("evidence_status"),
                "numerics_pass": row.get("numerics_pass"),
                "output_dir": row.get("output_dir"),
                "metrics_file": row.get("metrics_file"),
                "data_files": row.get("data_files", []),
                "artifact_inventory": row.get("artifact_inventory", {}),
                "key_metrics": row.get("key_metrics", {}),
                "source_file": _maybe_relative(REGISTRY_DIR / "campaign_manifest.json"),
            }
        )
    return normalized


def build_metric_summaries() -> list[dict[str, Any]]:
    source = REGISTRY_DIR / "master_uncertainty.csv"
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            for metric in METRICS:
                n = _safe_int(raw.get(f"{metric}_n"))
                mean = _safe_float(raw.get(f"{metric}_mean"))
                if n is None or mean is None:
                    continue
                rows.append(
                    {
                        "group_level": raw.get("group_level"),
                        "campaign_id": raw.get("campaign_id"),
                        "family": raw.get("family"),
                        "target_style": raw.get("target_style") or None,
                        "n_sites": _safe_int(raw.get("n_sites")),
                        "regime_label": raw.get("regime_label") or None,
                        "metric": metric,
                        "n": n,
                        "mean": mean,
                        "std": _safe_float(raw.get(f"{metric}_std")),
                        "sem": _safe_float(raw.get(f"{metric}_sem")),
                        "ci95_low": _safe_float(raw.get(f"{metric}_ci95_low")),
                        "ci95_high": _safe_float(raw.get(f"{metric}_ci95_high")),
                        "source_file": _maybe_relative(source),
                    }
                )
    return rows


def build_entropy_summary(metric_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    wanted = {"entropy", "purity", "coherence", "participation_ratio", "ipr", "arrival"}
    for row in metric_summaries:
        if row["group_level"] != "campaign_family" or row["metric"] not in wanted:
            continue
        key = (row["campaign_id"], row["family"], row.get("source_file") or "")
        item = by_key.setdefault(
            key,
            {
                "campaign_id": row["campaign_id"],
                "family": row["family"],
                "source_file": row["source_file"],
            },
        )
        metric = row["metric"]
        item[f"{metric}_n"] = row["n"]
        item[f"{metric}_mean"] = row["mean"]
        item[f"{metric}_ci95_low"] = row["ci95_low"]
        item[f"{metric}_ci95_high"] = row["ci95_high"]
    rows = list(by_key.values())
    rows.sort(key=lambda item: item.get("entropy_mean") if item.get("entropy_mean") is not None else -1.0, reverse=True)
    return {
        "meaning": "Graph-normalized von Neumann entropy measures mixing of the remaining graph state; it is not target arrival and must not be used alone as transport success.",
        "rows": rows,
    }


def build_quantum_classical_summary(metric_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for row in metric_summaries:
        if row["group_level"] != "campaign_family" or row["metric"] != "quantum_minus_classical":
            continue
        rows.append(
            {
                "campaign_id": row["campaign_id"],
                "family": row["family"],
                "n": row["n"],
                "mean": row["mean"],
                "ci95_low": row["ci95_low"],
                "ci95_high": row["ci95_high"],
                "verdict": _verdict_for_quantum_classical(row["mean"], row["ci95_low"], row["ci95_high"]),
                "source_file": row["source_file"],
            }
        )
    rows.sort(key=lambda item: item["mean"], reverse=True)
    return {
        "meaning": "best open-quantum target arrival minus classical target arrival on the same graph/control.",
        "threshold": "quantum_higher requires mean > 0.05 and CI95 low > 0.",
        "rows": rows,
    }


def build_claims() -> dict[str, Any]:
    claims = _read_json(REGISTRY_DIR / "master_claims.json", {})
    if not isinstance(claims, dict):
        claims = {}
    claims["source_file"] = _maybe_relative(REGISTRY_DIR / "master_claims.json")
    return claims


def build_paper_guardrails(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    guardrail_files = []
    for path in sorted((ROOT / "outputs" / "transport_networks").rglob("literature_guardrails.json")):
        guardrail_files.append(
            {
                "path": _maybe_relative(path),
                "source_campaign": _campaign_id_from_path(path, campaigns),
                "size_bytes": path.stat().st_size,
            }
        )

    suite_dir = ROOT / "outputs" / "transport_networks" / "paper_reproduction_suite" / "latest"
    return {
        "meaning": "Paper guardrails compare lab outputs against literature expectations. Profile pages are not used as proof.",
        "guardrail_files": guardrail_files,
        "paper_reproduction_suite": {
            "paper_verdicts": _read_json(suite_dir / "paper_verdicts.json", {}),
            "paper_claims": _read_json(suite_dir / "paper_claims.json", {}),
            "paper_reproduction_score": _read_json(suite_dir / "paper_reproduction_score.json", {}),
            "literature_guardrails": _read_json(suite_dir / "literature_guardrails.json", {}),
            "source_campaign": "paper_reproduction_suite",
        },
    }


def build_artifact_catalog(campaigns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    figures = []
    for path in sorted((ROOT / "outputs" / "transport_networks").rglob("*")):
        if path.suffix.lower() not in {".png", ".gif"} or not path.is_file():
            continue
        figures.append(
            {
                "path": _maybe_relative(path),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "source_campaign": _campaign_id_from_path(path, campaigns),
            }
        )

    notebooks = []
    notebook_dir = ROOT / "notebooks"
    if notebook_dir.exists():
        for path in sorted(notebook_dir.glob("*.ipynb")):
            notebooks.append(
                {
                    "path": _maybe_relative(path),
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "role": "colab_presentation" if "colab" in path.name else "lab_notebook",
                    "source_file": _maybe_relative(path),
                }
            )

    reports = []
    for base in [ROOT / "reports", ROOT / "outputs" / "transport_networks"]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in {".md", ".pdf", ".tex"} or not path.is_file():
                continue
            reports.append(
                {
                    "path": _maybe_relative(path),
                    "name": path.name,
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "source_campaign": _campaign_id_from_path(path, campaigns),
                }
            )
    return figures, notebooks, reports


def build_index(output_dir: Path = INDEX_DIR) -> BuiltMcpIndex:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    master_metrics = _read_json(REGISTRY_DIR / "master_metrics.json", {})
    campaigns = load_campaigns()
    metric_summaries = build_metric_summaries()
    entropy_summary = build_entropy_summary(metric_summaries)
    quantum_classical_summary = build_quantum_classical_summary(metric_summaries)
    claims = build_claims()
    paper_guardrails = build_paper_guardrails(campaigns)
    figures, notebooks, reports = build_artifact_catalog(campaigns)

    files = {
        "campaigns": output_dir / "campaigns.json",
        "metric_summaries": output_dir / "metric_summaries.json",
        "entropy_summary": output_dir / "entropy_summary.json",
        "quantum_classical_summary": output_dir / "quantum_classical_summary.json",
        "claims": output_dir / "claims.json",
        "paper_guardrails": output_dir / "paper_guardrails.json",
        "figures": output_dir / "figures.json",
        "notebooks": output_dir / "notebooks.json",
        "reports": output_dir / "reports.json",
    }

    _write_json(files["campaigns"], {"generated_at_utc": generated_at, "source_file": _maybe_relative(REGISTRY_DIR / "campaign_manifest.json"), "campaigns": campaigns})
    _write_json(files["metric_summaries"], {"generated_at_utc": generated_at, "metrics": METRICS, "rows": metric_summaries})
    _write_json(files["entropy_summary"], {"generated_at_utc": generated_at, **entropy_summary})
    _write_json(files["quantum_classical_summary"], {"generated_at_utc": generated_at, **quantum_classical_summary})
    _write_json(files["claims"], {"generated_at_utc": generated_at, **claims})
    _write_json(files["paper_guardrails"], {"generated_at_utc": generated_at, **paper_guardrails})
    _write_json(files["figures"], {"generated_at_utc": generated_at, "figures": figures})
    _write_json(files["notebooks"], {"generated_at_utc": generated_at, "notebooks": notebooks})
    _write_json(files["reports"], {"generated_at_utc": generated_at, "reports": reports})

    index_path = output_dir / "index.json"
    index_payload = {
        "generated_at_utc": generated_at,
        "schema_version": 1,
        "role": "read_only_research_hub_index",
        "root": str(ROOT),
        "registry_dir": _maybe_relative(REGISTRY_DIR),
        "source_of_truth": "outputs/transport_networks/lab_registry/latest",
        "master_metrics": master_metrics,
        "counts": {
            "campaigns": len(campaigns),
            "metric_rows": len(metric_summaries),
            "entropy_rows": len(entropy_summary["rows"]),
            "quantum_classical_rows": len(quantum_classical_summary["rows"]),
            "figures": len(figures),
            "notebooks": len(notebooks),
            "reports": len(reports),
        },
        "files": {name: _maybe_relative(path) for name, path in files.items()},
    }
    _write_json(index_path, index_payload)
    files = {"index": index_path, **files}
    return BuiltMcpIndex(output_dir=output_dir, files=files)


if __name__ == "__main__":
    built = build_index()
    print(json.dumps({"output_dir": str(built.output_dir), "files": built.to_dict()}, indent=2, ensure_ascii=False))
