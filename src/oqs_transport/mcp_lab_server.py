from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REGISTRY_RELATIVE_PATH = Path("outputs") / "transport_networks" / "lab_registry" / "latest"
MCP_INDEX_RELATIVE_PATH = Path("outputs") / "transport_networks" / "mcp_index" / "latest"

READ_ONLY_TOOL_NAMES = [
    "get_lab_status",
    "list_campaigns",
    "get_campaign_summary",
    "get_campaign",
    "get_campaign_metrics",
    "get_lab_memory",
    "get_claims",
    "get_critic_report",
    "compare_families",
    "summarize_entropy",
    "quantum_classical_summary",
    "get_paper_guardrails",
    "list_figures",
    "list_notebooks",
    "list_reports",
    "read_campaign_file",
    "suggest_next_campaign",
]


def _project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compact_row(row: dict[str, str], metric: str) -> dict[str, Any]:
    mean = _safe_float(row.get(f"{metric}_mean"))
    ci_low = _safe_float(row.get(f"{metric}_ci95_low"))
    ci_high = _safe_float(row.get(f"{metric}_ci95_high"))
    n = _safe_float(row.get(f"{metric}_n"))
    return {
        "campaign_id": row.get("campaign_id", ""),
        "family": row.get("family", ""),
        "n": int(n) if n is not None else None,
        "mean": mean,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
    }


@dataclass(frozen=True)
class TransportLabMcpData:
    """Read-only access layer for the transport laboratory outputs."""

    root: Path
    registry_dir: Path
    index_dir: Path

    @classmethod
    def from_root(cls, root: str | Path | None = None) -> "TransportLabMcpData":
        project_root = _project_root(Path(root) if root else None)
        return cls(
            root=project_root,
            registry_dir=project_root / REGISTRY_RELATIVE_PATH,
            index_dir=project_root / MCP_INDEX_RELATIVE_PATH,
        )

    def index_exists(self) -> bool:
        return (self.index_dir / "index.json").exists()

    def data_source(self) -> str:
        return "mcp_index" if self.index_exists() else "lab_registry_fallback"

    def _index_payload(self, name: str, default: Any) -> Any:
        return _read_json(self.index_dir / f"{name}.json", default)

    def status(self) -> dict[str, Any]:
        metrics = self.master_metrics()
        index_payload = self._index_payload("index", {})
        return {
            "root": str(self.root),
            "registry_dir": str(self.registry_dir),
            "index_dir": str(self.index_dir),
            "registry_exists": self.registry_dir.exists(),
            "index_exists": self.index_exists(),
            "data_source": self.data_source(),
            "fallback_warning": None if self.index_exists() else "mcp_index/latest not found; serving directly from lab_registry/latest.",
            "tool_count": len(READ_ONLY_TOOL_NAMES),
            "tools": READ_ONLY_TOOL_NAMES,
            "campaign_count": metrics.get("campaign_count", 0),
            "master_result_count": metrics.get("master_result_count", 0),
            "scientific_candidate_campaigns": metrics.get("scientific_candidate_campaigns", []),
            "smoke_only_campaigns": metrics.get("smoke_only_campaigns", []),
            "index_counts": index_payload.get("counts", {}),
        }

    def get_lab_status(self) -> dict[str, Any]:
        return self.status()

    def master_metrics(self) -> dict[str, Any]:
        index_payload = self._index_payload("index", {})
        if isinstance(index_payload, dict) and index_payload.get("master_metrics"):
            return index_payload.get("master_metrics", {})
        return _read_json(self.registry_dir / "master_metrics.json", {})

    def manifest(self) -> list[dict[str, Any]]:
        indexed = self._index_payload("campaigns", {})
        if isinstance(indexed, dict) and isinstance(indexed.get("campaigns"), list):
            return indexed["campaigns"]
        payload = _read_json(self.registry_dir / "campaign_manifest.json", [])
        return payload if isinstance(payload, list) else []

    def list_campaigns(self, evidence_status: str | None = None) -> dict[str, Any]:
        campaigns = self.manifest()
        if evidence_status:
            campaigns = [row for row in campaigns if row.get("evidence_status") == evidence_status]
        return {
            "data_source": self.data_source(),
            "count": len(campaigns),
            "campaigns": [
                {
                    "campaign_id": row.get("campaign_id"),
                    "script": row.get("script"),
                    "profile": row.get("profile"),
                    "status": row.get("status"),
                    "evidence_status": row.get("evidence_status"),
                    "numerics_pass": row.get("numerics_pass"),
                    "output_dir": row.get("output_dir"),
                    "key_metrics": row.get("key_metrics", {}),
                    "source_file": row.get("source_file"),
                }
                for row in campaigns
            ],
        }

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        for row in self.manifest():
            if row.get("campaign_id") == campaign_id:
                return row
        return {"error": f"Unknown campaign_id: {campaign_id}", "known_campaigns": [r.get("campaign_id") for r in self.manifest()]}

    def get_campaign_summary(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.get_campaign(campaign_id)
        if "error" in campaign:
            return campaign
        metric_rows = [
            row
            for row in self._metric_summary_rows()
            if row.get("group_level") == "campaign_family" and row.get("campaign_id") == campaign_id
        ]
        return {
            "data_source": self.data_source(),
            "campaign": campaign,
            "metric_rows": metric_rows,
            "metrics_file_payload": self.get_campaign_metrics(campaign_id),
        }

    def get_campaign_metrics(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.get_campaign(campaign_id)
        if "error" in campaign:
            return campaign
        metrics_path = Path(str(campaign.get("metrics_file", "")))
        metrics = _read_json(metrics_path, {})
        return {
            "campaign_id": campaign_id,
            "metrics_file": str(metrics_path) if metrics_path else "",
            "key_metrics": campaign.get("key_metrics", {}),
            "metrics": metrics,
        }

    def get_lab_memory(self) -> str:
        return _read_text(self.registry_dir / "transport_lab_memory.md", "No lab memory file was found.")

    def get_claims(self, status: str = "all") -> dict[str, Any]:
        claims = self._index_payload("claims", {})
        if not claims:
            claims = _read_json(self.registry_dir / "master_claims.json", {})
        allowed = claims.get("allowed_claims", [])
        blocked = claims.get("blocked_claims", [])
        if status == "allowed":
            return {"data_source": self.data_source(), "allowed_claims": allowed}
        if status == "blocked":
            return {"data_source": self.data_source(), "blocked_claims": blocked}
        return {"data_source": self.data_source(), "allowed_claims": allowed, "blocked_claims": blocked}

    def get_critic_report(self) -> str:
        return _read_text(self.registry_dir / "master_critic_report.md", "No critic report file was found.")

    def _uncertainty_rows(self) -> list[dict[str, str]]:
        path = self.registry_dir / "master_uncertainty.csv"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _metric_summary_rows(self) -> list[dict[str, Any]]:
        indexed = self._index_payload("metric_summaries", {})
        if isinstance(indexed, dict) and isinstance(indexed.get("rows"), list):
            return indexed["rows"]
        rows: list[dict[str, Any]] = []
        for raw in self._uncertainty_rows():
            for metric in [
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
            ]:
                compact = _compact_row(raw, metric)
                if compact["mean"] is None or compact["n"] is None:
                    continue
                rows.append(
                    {
                        "group_level": raw.get("group_level"),
                        "campaign_id": raw.get("campaign_id"),
                        "family": raw.get("family"),
                        "target_style": raw.get("target_style") or None,
                        "n_sites": _safe_float(raw.get("n_sites")),
                        "regime_label": raw.get("regime_label") or None,
                        "metric": metric,
                        **compact,
                        "source_file": str(self.registry_dir / "master_uncertainty.csv"),
                    }
                )
        return rows

    def compare_families(self, metric: str = "arrival", campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for row in self._metric_summary_rows():
            if row.get("group_level") != "campaign_family" or row.get("metric") != metric:
                continue
            if campaign_id and row.get("campaign_id") != campaign_id:
                continue
            rows.append(
                {
                    "campaign_id": row.get("campaign_id"),
                    "family": row.get("family"),
                    "n": row.get("n"),
                    "mean": row.get("mean"),
                    "ci95_low": row.get("ci95_low"),
                    "ci95_high": row.get("ci95_high"),
                    "source_file": row.get("source_file"),
                }
            )
        rows.sort(key=lambda item: item["mean"], reverse=True)
        return {"data_source": self.data_source(), "metric": metric, "campaign_id": campaign_id, "count": len(rows), "rows": rows[:top_n]}

    def summarize_entropy(self, campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        indexed = self._index_payload("entropy_summary", {})
        if isinstance(indexed, dict) and isinstance(indexed.get("rows"), list):
            rows = indexed["rows"]
            meaning = indexed.get(
                "meaning",
                "Entropy is graph-normalized von Neumann entropy of the remaining graph state; it measures mixing, not target success.",
            )
        else:
            rows = []
            for row in self._uncertainty_rows():
                if row.get("group_level") != "campaign_family":
                    continue
                entropy = _compact_row(row, "entropy")
                purity = _compact_row(row, "purity")
                participation = _compact_row(row, "participation_ratio")
                if entropy["mean"] is None:
                    continue
                rows.append(
                    {
                        "campaign_id": entropy["campaign_id"],
                        "family": entropy["family"],
                        "entropy_n": entropy["n"],
                        "entropy_mean": entropy["mean"],
                        "entropy_ci95_low": entropy["ci95_low"],
                        "entropy_ci95_high": entropy["ci95_high"],
                        "purity_mean": purity["mean"],
                        "participation_ratio_mean": participation["mean"],
                        "source_file": str(self.registry_dir / "master_uncertainty.csv"),
                    }
                )
            meaning = "Entropy is graph-normalized von Neumann entropy of the remaining graph state; it measures mixing, not target success."
        if campaign_id:
            rows = [row for row in rows if row.get("campaign_id") == campaign_id]
        rows.sort(key=lambda item: item["entropy_mean"], reverse=True)
        return {
            "data_source": self.data_source(),
            "meaning": meaning,
            "campaign_id": campaign_id,
            "count": len(rows),
            "rows": rows[:top_n],
        }

    def quantum_classical_summary(self, campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        indexed = self._index_payload("quantum_classical_summary", {})
        if isinstance(indexed, dict) and isinstance(indexed.get("rows"), list):
            rows = indexed["rows"]
            meaning = indexed.get("meaning", "best open-quantum target arrival minus classical target arrival on the same graph/control.")
        else:
            rows = self.compare_families("quantum_minus_classical", campaign_id=campaign_id, top_n=10_000)["rows"]
            for row in rows:
                mean = row.get("mean")
                ci_low = row.get("ci95_low")
                ci_high = row.get("ci95_high")
                if mean is None or ci_low is None or ci_high is None:
                    row["verdict"] = "inconclusive"
                elif mean > 0.05 and ci_low > 0:
                    row["verdict"] = "quantum_higher"
                elif abs(mean) < 0.05 or ci_low <= 0 <= ci_high:
                    row["verdict"] = "classical_explains_or_inconclusive"
                elif mean < -0.05 and ci_high < 0:
                    row["verdict"] = "classical_higher"
                else:
                    row["verdict"] = "inconclusive"
            meaning = "best open-quantum target arrival minus classical target arrival on the same graph/control."
        if campaign_id:
            rows = [row for row in rows if row.get("campaign_id") == campaign_id]
        rows = rows[:top_n]
        return {
            "data_source": self.data_source(),
            "metric": meaning,
            "campaign_id": campaign_id,
            "rows": rows,
        }

    def get_paper_guardrails(self) -> dict[str, Any]:
        payload = self._index_payload("paper_guardrails", {})
        if payload:
            return {"data_source": self.data_source(), **payload}
        suite_dir = self.root / "outputs" / "transport_networks" / "paper_reproduction_suite" / "latest"
        return {
            "data_source": self.data_source(),
            "meaning": "Fallback paper guardrail payload from paper_reproduction_suite/latest.",
            "paper_reproduction_suite": {
                "paper_verdicts": _read_json(suite_dir / "paper_verdicts.json", {}),
                "paper_claims": _read_json(suite_dir / "paper_claims.json", {}),
                "paper_reproduction_score": _read_json(suite_dir / "paper_reproduction_score.json", {}),
                "literature_guardrails": _read_json(suite_dir / "literature_guardrails.json", {}),
                "source_campaign": "paper_reproduction_suite",
            },
        }

    def list_figures(self, campaign_id: str | None = None, suffix: str | None = None, limit: int = 100) -> dict[str, Any]:
        payload = self._index_payload("figures", {})
        figures = payload.get("figures", []) if isinstance(payload, dict) else []
        if campaign_id:
            figures = [row for row in figures if row.get("source_campaign") == campaign_id]
        if suffix:
            normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
            figures = [row for row in figures if row.get("suffix") == normalized_suffix.lower()]
        return {"data_source": self.data_source(), "count": len(figures), "figures": figures[:limit]}

    def list_notebooks(self, role: str | None = None) -> dict[str, Any]:
        payload = self._index_payload("notebooks", {})
        notebooks = payload.get("notebooks", []) if isinstance(payload, dict) else []
        if role:
            notebooks = [row for row in notebooks if row.get("role") == role]
        return {"data_source": self.data_source(), "count": len(notebooks), "notebooks": notebooks}

    def list_reports(self, campaign_id: str | None = None, suffix: str | None = None, limit: int = 100) -> dict[str, Any]:
        payload = self._index_payload("reports", {})
        reports = payload.get("reports", []) if isinstance(payload, dict) else []
        if campaign_id:
            reports = [row for row in reports if row.get("source_campaign") == campaign_id]
        if suffix:
            normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
            reports = [row for row in reports if row.get("suffix") == normalized_suffix.lower()]
        return {"data_source": self.data_source(), "count": len(reports), "reports": reports[:limit]}

    def read_campaign_file(self, campaign_id: str, filename: str, max_chars: int = 20_000) -> dict[str, Any]:
        campaign = self.get_campaign(campaign_id)
        if "error" in campaign:
            return campaign
        output_dir = Path(str(campaign.get("output_dir", ""))).resolve()
        requested = (output_dir / filename).resolve()
        if output_dir not in [requested, *requested.parents]:
            return {"error": "Refusing to read outside the campaign output directory."}
        if not requested.exists() or not requested.is_file():
            return {"error": f"File not found inside campaign output directory: {filename}"}
        text = requested.read_text(encoding="utf-8", errors="replace")
        return {
            "campaign_id": campaign_id,
            "filename": filename,
            "truncated": len(text) > max_chars,
            "content": text[:max_chars],
        }

    def suggest_next_campaign(self) -> dict[str, Any]:
        metrics = self.master_metrics()
        blocked = self.get_claims("blocked").get("blocked_claims", [])
        smoke_only = set(metrics.get("smoke_only_campaigns", []))
        if "dynamic_network_atlas" in smoke_only:
            return {
                "next_action": "run_dynamic_network_atlas_strong_on_idle_machine",
                "reason": "The atlas campaign exists only as smoke-level evidence; strong conclusions need the non-smoke strong profile.",
                "command": "python scripts/run_transport_dynamic_network_atlas.py --profile strong",
                "guardrail": "Use resume/chunks if the run is interrupted. Do not promote claims until CI95, classical control, and critic pass.",
                "blocked_claims_considered": blocked,
            }
        return {
            "next_action": "refine_strongest_blocked_or_borderline_claim",
            "reason": "No smoke-only atlas blocker was found. Use the critic report to select the most under-resolved claim.",
            "blocked_claims_considered": blocked,
        }


def create_fastmcp_server(root: str | Path | None = None) -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The Python package 'mcp' is not installed. Install it in this environment "
            "before running the stdio MCP server. The read-only --check mode does not require it."
        ) from exc

    data = TransportLabMcpData.from_root(root)
    server = FastMCP("transport-lab")

    @server.tool()
    def get_lab_status() -> dict[str, Any]:
        return data.get_lab_status()

    @server.tool()
    def list_campaigns(evidence_status: str | None = None) -> dict[str, Any]:
        return data.list_campaigns(evidence_status=evidence_status)

    @server.tool()
    def get_campaign_summary(campaign_id: str) -> dict[str, Any]:
        return data.get_campaign_summary(campaign_id)

    @server.tool()
    def get_campaign(campaign_id: str) -> dict[str, Any]:
        return data.get_campaign(campaign_id)

    @server.tool()
    def get_campaign_metrics(campaign_id: str) -> dict[str, Any]:
        return data.get_campaign_metrics(campaign_id)

    @server.tool()
    def get_lab_memory() -> str:
        return data.get_lab_memory()

    @server.tool()
    def get_claims(status: str = "all") -> dict[str, Any]:
        return data.get_claims(status=status)

    @server.tool()
    def get_critic_report() -> str:
        return data.get_critic_report()

    @server.tool()
    def compare_families(metric: str = "arrival", campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        return data.compare_families(metric=metric, campaign_id=campaign_id, top_n=top_n)

    @server.tool()
    def summarize_entropy(campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        return data.summarize_entropy(campaign_id=campaign_id, top_n=top_n)

    @server.tool()
    def quantum_classical_summary(campaign_id: str | None = None, top_n: int = 20) -> dict[str, Any]:
        return data.quantum_classical_summary(campaign_id=campaign_id, top_n=top_n)

    @server.tool()
    def get_paper_guardrails() -> dict[str, Any]:
        return data.get_paper_guardrails()

    @server.tool()
    def list_figures(campaign_id: str | None = None, suffix: str | None = None, limit: int = 100) -> dict[str, Any]:
        return data.list_figures(campaign_id=campaign_id, suffix=suffix, limit=limit)

    @server.tool()
    def list_notebooks(role: str | None = None) -> dict[str, Any]:
        return data.list_notebooks(role=role)

    @server.tool()
    def list_reports(campaign_id: str | None = None, suffix: str | None = None, limit: int = 100) -> dict[str, Any]:
        return data.list_reports(campaign_id=campaign_id, suffix=suffix, limit=limit)

    @server.tool()
    def read_campaign_file(campaign_id: str, filename: str, max_chars: int = 20_000) -> dict[str, Any]:
        return data.read_campaign_file(campaign_id=campaign_id, filename=filename, max_chars=max_chars)

    @server.tool()
    def suggest_next_campaign() -> dict[str, Any]:
        return data.suggest_next_campaign()

    @server.resource("transport-lab://memory")
    def lab_memory_resource() -> str:
        return data.get_lab_memory()

    @server.resource("transport-lab://status")
    def status_resource() -> str:
        return json.dumps(data.get_lab_status(), indent=2, ensure_ascii=False)

    @server.resource("transport-lab://campaigns")
    def campaigns_resource() -> str:
        return json.dumps(data.list_campaigns(), indent=2, ensure_ascii=False)

    @server.resource("transport-lab://claims")
    def claims_resource() -> str:
        return json.dumps(data.get_claims(), indent=2, ensure_ascii=False)

    @server.resource("transport-lab://notebooks")
    def notebooks_resource() -> str:
        return json.dumps(data.list_notebooks(), indent=2, ensure_ascii=False)

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only MCP server for the open-quantum transport lab.")
    parser.add_argument("--root", default=None, help="Project root. Defaults to auto-detection.")
    parser.add_argument("--check", action="store_true", help="Print registry status without requiring the mcp package.")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="MCP transport for FastMCP.")
    args = parser.parse_args(argv)

    if args.check:
        print(json.dumps(TransportLabMcpData.from_root(args.root).status(), indent=2, ensure_ascii=False))
        return 0

    server = create_fastmcp_server(args.root)
    server.run(transport=args.transport)
    return 0


__all__ = [
    "READ_ONLY_TOOL_NAMES",
    "TransportLabMcpData",
    "create_fastmcp_server",
    "main",
]
