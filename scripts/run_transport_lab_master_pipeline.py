from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import mean_std_sem_ci95  # noqa: E402


TRANSPORT_ROOT = ROOT / "outputs" / "transport_networks"
REGISTRY_DIR = TRANSPORT_ROOT / "lab_registry" / "latest"
REPORT_DIR = TRANSPORT_ROOT / "master_scientific_report" / "latest"
NOTEBOOK_PATH = ROOT / "notebooks" / "transport_lab_master_notebook.ipynb"

CAMPAIGN_SPECS = [
    {
        "campaign_id": "research_journey_v2",
        "script": "scripts/run_transport_research_journey_v2.py",
        "output": TRANSPORT_ROOT / "research_journey_v2" / "latest",
        "metrics": "metrics.json",
        "data_files": ["target_geometry_records.csv", "quantum_classical_comparison.csv", "fractal_transport_summary.csv"],
    },
    {
        "campaign_id": "target_geometry_confirm",
        "script": "scripts/run_transport_target_geometry_confirm.py",
        "output": TRANSPORT_ROOT / "target_geometry_confirm" / "latest",
        "metrics": "metrics.json",
        "data_files": ["target_all_sites_records.csv", "target_pair_confirmations.csv", "controlled_pair_tests.csv", "quantum_classical_target_controls.csv"],
    },
    {
        "campaign_id": "fractal_geometry_followup",
        "script": "scripts/run_transport_fractal_geometry_followup.py",
        "output": TRANSPORT_ROOT / "fractal_geometry_followup" / "latest",
        "metrics": "metrics.json",
        "data_files": ["fractal_scaling_summary.csv"],
    },
    {
        "campaign_id": "paper_reproduction_suite",
        "script": "scripts/run_transport_paper_reproduction_suite.py",
        "output": TRANSPORT_ROOT / "paper_reproduction_suite" / "latest",
        "metrics": "paper_suite_metrics.json",
        "data_files": ["dynamic_signatures_with_classical.csv", "statistical_summary.csv", "paper_reproduction_table.csv"],
    },
    {
        "campaign_id": "network_classification_complete",
        "script": "scripts/build_transport_network_classification_pack.py",
        "output": TRANSPORT_ROOT / "network_classification_complete" / "latest",
        "metrics": "metrics.json",
        "data_files": [],
    },
    {
        "campaign_id": "dynamic_network_atlas",
        "script": "scripts/run_transport_dynamic_network_atlas.py",
        "output": TRANSPORT_ROOT / "dynamic_network_atlas" / "latest",
        "metrics": "atlas_metrics.json",
        "data_files": ["atlas_records.csv", "quantum_classical_delta.csv", "atlas_summary_by_family.csv", "atlas_summary_by_target.csv"],
    },
    {
        "campaign_id": "dynamic_network_atlas_evidence_prep",
        "script": "scripts/run_transport_dynamic_network_atlas.py --profile evidence_prep",
        "output": TRANSPORT_ROOT / "dynamic_network_atlas_evidence_prep" / "latest",
        "metrics": "atlas_metrics.json",
        "data_files": ["atlas_records.csv", "quantum_classical_delta.csv", "atlas_summary_by_family.csv", "atlas_summary_by_target.csv"],
    },
    {
        "campaign_id": "dynamic_network_atlas_intense",
        "script": "scripts/run_transport_dynamic_network_atlas.py --profile intense",
        "output": TRANSPORT_ROOT / "dynamic_network_atlas_intense" / "latest",
        "metrics": "atlas_metrics.json",
        "data_files": ["atlas_records.csv", "quantum_classical_delta.csv", "atlas_summary_by_family.csv", "atlas_summary_by_target.csv"],
    },
]

METRIC_ALIASES = {
    "arrival": ("arrival", "best_arrival", "target_arrival", "best_arrival_mean"),
    "zero_dephasing_arrival": ("zero_dephasing_arrival", "zero_arrival"),
    "gain": ("dephasing_gain", "gain", "dephasing_gain_mean"),
    "entropy": ("best_final_entropy", "final_entropy", "best_final_entropy_mean", "final_entropy_mean"),
    "purity": ("best_final_purity", "final_purity", "best_final_purity_mean"),
    "shannon_entropy": ("best_population_shannon_entropy", "population_shannon_entropy", "population_shannon_entropy_mean"),
    "coherence": ("best_mean_coherence_l1", "mean_coherence_l1", "best_mean_coherence_l1_mean"),
    "participation_ratio": ("best_participation_ratio", "participation_ratio", "best_participation_ratio_mean"),
    "ipr": ("best_ipr", "ipr", "best_ipr_mean"),
    "msd": ("best_final_msd", "final_msd", "final_msd_mean"),
    "front_width": ("best_final_front_width", "final_front_width", "final_front_width_mean"),
    "quantum_minus_classical": ("quantum_minus_classical", "arrival_quantum_minus_classical", "mean_quantum_classical_delta"),
    "classical_arrival": ("classical_arrival", "arrival_classical"),
    "sink_hitting_time": ("best_sink_hitting_time_filled", "sink_hitting_time_filled", "best_sink_hitting_time_filled_mean"),
}

MASTER_METRICS = (
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
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _as_float(value: object, default: float = np.nan) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return out if np.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def _first_float(row: dict[str, object], names: Iterable[str]) -> float:
    for name in names:
        if name in row:
            value = _as_float(row.get(name))
            if np.isfinite(value):
                return value
    return np.nan


def _first_text(row: dict[str, object], names: Iterable[str], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return default


def _profile_from(metrics: dict[str, object], config: dict[str, object]) -> str:
    profile = str(metrics.get("profile") or metrics.get("paper_suite_profile") or config.get("profile") or "unknown")
    return profile.lower()


def _evidence_status(campaign_id: str, profile: str, metrics: dict[str, object]) -> str:
    if profile == "smoke":
        return "smoke_only"
    if profile in {"paper", "strong", "confirm", "evidence_prep"}:
        return "scientific_candidate"
    if profile == "interactive":
        return "exploratory_interactive"
    if campaign_id == "network_classification_complete" and metrics:
        return "scientific_candidate"
    return "unknown"


def _artifact_inventory(output_dir: Path) -> dict[str, int]:
    if not output_dir.exists():
        return {}
    counts = Counter(path.suffix.lower() or "<none>" for path in output_dir.rglob("*") if path.is_file())
    return dict(sorted(counts.items()))


def _compact_metrics(metrics: dict[str, object]) -> dict[str, object]:
    keys = [
        "record_count",
        "target_record_count",
        "open_signature_count",
        "row_count",
        "family_count",
        "mean_best_arrival",
        "mean_quantum_minus_classical",
        "mean_quantum_classical_delta",
        "target_spread_mean",
        "strong_target_effect",
        "fractal_geometry_changes_spreading",
        "group_combined_accuracy",
        "combined_accuracy",
        "combined_baseline",
        "scientific_verdict",
        "paper_verdict_counts",
    ]
    return {key: metrics[key] for key in keys if key in metrics}


def build_campaign_manifest() -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for spec in CAMPAIGN_SPECS:
        output = Path(spec["output"])
        metrics = _read_json(output / str(spec["metrics"]))
        config = _read_json(output / "config_used.json")
        profile = _profile_from(metrics, config)
        data_files = [name for name in spec["data_files"] if (output / name).exists()]
        status = "present" if output.exists() else "missing"
        if output.exists() and not metrics:
            status = "present_no_metrics"
        manifest.append(
            {
                "campaign_id": spec["campaign_id"],
                "script": spec["script"],
                "output_dir": str(output),
                "status": status,
                "profile": profile,
                "evidence_status": _evidence_status(str(spec["campaign_id"]), profile, metrics),
                "numerics_pass": metrics.get("numerics_pass", None),
                "metrics_file": str(output / str(spec["metrics"])),
                "data_files": data_files,
                "artifact_inventory": _artifact_inventory(output),
                "key_metrics": _compact_metrics(metrics),
            }
        )
    return manifest


def _normalize_row(campaign_id: str, source_file: str, row: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {
        "campaign_id": campaign_id,
        "source_file": source_file,
        "family": _first_text(row, ("family",), "unknown"),
        "n_sites": _first_text(row, ("n_sites", "topology_n_sites"), ""),
        "instance_id": _first_text(row, ("instance_id", "validation_group_id"), ""),
        "graph_seed": _first_text(row, ("graph_seed",), ""),
        "disorder_seed": _first_text(row, ("disorder_seed",), ""),
        "target_style": _first_text(row, ("target_style", "target_label"), ""),
        "trap_site": _first_text(row, ("trap_site",), ""),
        "disorder_strength_over_coupling": _first_text(row, ("disorder_strength_over_coupling",), ""),
        "dephasing_over_coupling": _first_text(row, ("dephasing_over_coupling", "best_dephasing_over_coupling"), ""),
        "regime_label": _first_text(row, ("regime_label", "dominant_regime"), ""),
        "edge_model": _first_text(row, ("edge_model",), ""),
    }
    for canonical, aliases in METRIC_ALIASES.items():
        value = _first_float(row, aliases)
        out[canonical] = "" if not np.isfinite(value) else value
    for key in ("max_trace_deviation", "max_population_closure_error", "min_state_eigenvalue"):
        value = _first_float(row, (key,))
        out[key] = "" if not np.isfinite(value) else value
    return out


def build_master_results(manifest: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entry in manifest:
        campaign_id = str(entry["campaign_id"])
        output_dir = Path(str(entry["output_dir"]))
        for data_file in list(entry.get("data_files", [])):
            for row in _read_csv(output_dir / str(data_file)):
                normalized = _normalize_row(campaign_id, str(data_file), row)
                has_metric = any(normalized.get(metric, "") != "" for metric in MASTER_METRICS)
                if normalized["family"] == "unknown" and not has_metric:
                    continue
                rows.append(normalized)
    return rows


def _group_key(row: dict[str, object], group_names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(row.get(name, "")) for name in group_names)


def build_uncertainty(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    group_levels = {
        "campaign_family": ("campaign_id", "family"),
        "campaign_family_target": ("campaign_id", "family", "target_style"),
        "campaign_family_size": ("campaign_id", "family", "n_sites"),
        "campaign_family_regime": ("campaign_id", "family", "regime_label"),
    }
    output: list[dict[str, object]] = []
    for level, keys in group_levels.items():
        grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[_group_key(row, keys)].append(row)
        for group_values, items in sorted(grouped.items()):
            base: dict[str, object] = {"group_level": level}
            base.update({key: value for key, value in zip(keys, group_values, strict=False)})
            for metric in MASTER_METRICS:
                values = [_as_float(item.get(metric)) for item in items]
                values = [value for value in values if np.isfinite(value)]
                summary = mean_std_sem_ci95(values)
                for summary_key, summary_value in summary.items():
                    base[f"{metric}_{summary_key}"] = summary_value
            output.append(dict(base))
    return output


def _uncertainty_rows_for(uncertainty: list[dict[str, object]], *, level: str, metric: str) -> list[dict[str, object]]:
    rows = []
    for row in uncertainty:
        if str(row.get("group_level")) != level:
            continue
        if int(float(row.get(f"{metric}_n", 0))) <= 0:
            continue
        rows.append(row)
    return rows


def build_claims_and_critic(manifest: list[dict[str, object]], uncertainty: list[dict[str, object]]) -> tuple[dict[str, object], str]:
    campaign_status = {str(entry["campaign_id"]): str(entry["evidence_status"]) for entry in manifest}
    allowed: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    next_actions: list[str] = []

    for entry in manifest:
        if entry["evidence_status"] == "smoke_only":
            blocked.append(
                {
                    "claim": f"{entry['campaign_id']} is scientifically conclusive",
                    "reason": "Campaign profile is smoke; smoke validates plumbing only.",
                    "campaign_id": entry["campaign_id"],
                }
            )

    target_rows = _uncertainty_rows_for(uncertainty, level="campaign_family", metric="arrival")
    target_support = [
        row
        for row in target_rows
        if str(row.get("campaign_id")) == "research_journey_v2"
        and int(row.get("arrival_n", 0)) >= 20
        and float(row.get("arrival_ci95_high", 0.0)) > 0.0
    ]
    if target_support:
        allowed.append(
            {
                "claim": "Target arrival is measurable with uncertainty in the paper-level journey.",
                "campaign_id": "research_journey_v2",
                "supporting_families": [
                    {
                        "family": row.get("family"),
                        "n": row.get("arrival_n"),
                        "mean": row.get("arrival_mean"),
                        "ci95_low": row.get("arrival_ci95_low"),
                        "ci95_high": row.get("arrival_ci95_high"),
                    }
                    for row in target_support
                ],
            }
        )

    q_rows = _uncertainty_rows_for(uncertainty, level="campaign_family", metric="quantum_minus_classical")
    q_positive = [
        row
        for row in q_rows
        if int(row.get("quantum_minus_classical_n", 0)) >= 10
        and float(row.get("quantum_minus_classical_mean", 0.0)) > 0.05
        and float(row.get("quantum_minus_classical_ci95_low", -1.0)) > 0.0
        and campaign_status.get(str(row.get("campaign_id"))) != "smoke_only"
    ]
    if q_positive:
        allowed.append(
            {
                "claim": "Some families show quantum-higher target arrival against the classical control.",
                "rule": "mean quantum_minus_classical > 0.05 and CI95 low > 0",
                "supporting_groups": [
                    {
                        "campaign_id": row.get("campaign_id"),
                        "family": row.get("family"),
                        "mean": row.get("quantum_minus_classical_mean"),
                        "ci95_low": row.get("quantum_minus_classical_ci95_low"),
                        "n": row.get("quantum_minus_classical_n"),
                    }
                    for row in q_positive[:10]
                ],
            }
        )
    else:
        blocked.append(
            {
                "claim": "Open-quantum signatures are stronger than the classical control.",
                "reason": "No non-smoke group currently satisfies mean > 0.05 with CI95 low > 0 in the master table.",
            }
        )

    gain_rows = _uncertainty_rows_for(uncertainty, level="campaign_family", metric="gain")
    gain_positive = [
        row
        for row in gain_rows
        if int(row.get("gain_n", 0)) >= 10
        and float(row.get("gain_mean", 0.0)) >= 0.05
        and float(row.get("gain_ci95_low", -1.0)) > 0.0
        and campaign_status.get(str(row.get("campaign_id"))) != "smoke_only"
    ]
    if gain_positive:
        allowed.append(
            {
                "claim": "Dephasing-assisted transport appears in selected non-smoke campaign/family groups.",
                "rule": "gain mean >= 0.05 and CI95 low > 0",
                "supporting_groups": [
                    {
                        "campaign_id": row.get("campaign_id"),
                        "family": row.get("family"),
                        "mean": row.get("gain_mean"),
                        "ci95_low": row.get("gain_ci95_low"),
                        "n": row.get("gain_n"),
                    }
                    for row in gain_positive[:10]
                ],
            }
        )
    else:
        blocked.append(
            {
                "claim": "Strong environment-assisted transport is established across the lab.",
                "reason": "Current master aggregation does not yet satisfy gain >= 0.05 with CI95 low > 0 in enough audited groups.",
            }
        )

    under_sampled = [
        {
            "campaign_id": row.get("campaign_id"),
            "family": row.get("family"),
            "metric": "arrival",
            "n": row.get("arrival_n"),
        }
        for row in target_rows
        if 0 < int(row.get("arrival_n", 0)) < 10 and campaign_status.get(str(row.get("campaign_id"))) != "smoke_only"
    ]
    if under_sampled:
        blocked.append(
            {
                "claim": "All family-level boundaries are resolved.",
                "reason": "Some non-smoke groups are under-sampled.",
                "examples": under_sampled[:12],
            }
        )

    paper_verdict_path = TRANSPORT_ROOT / "paper_reproduction_suite" / "latest" / "paper_verdicts.json"
    if paper_verdict_path.exists():
        allowed.append(
            {
                "claim": "Paper-by-paper guardrails are available for interpretation.",
                "campaign_id": "paper_reproduction_suite",
                "source": str(paper_verdict_path),
            }
        )
    else:
        blocked.append({"claim": "Paper guardrails are complete.", "reason": "paper_verdicts.json not found."})

    if campaign_status.get("dynamic_network_atlas") == "smoke_only":
        next_actions.append("Run the dynamic network atlas with profile strong, then rerun registry_only.")
    if q_positive:
        next_actions.append("Refine families with positive quantum-minus-classical CI95 before widening new themes.")
    else:
        next_actions.append("Prioritize stronger quantum-vs-classical controls on target/geometric cases.")

    lines = ["# Master Critic Report", "", "## Allowed Claims", ""]
    lines.extend([f"- {item['claim']}" for item in allowed] or ["- None yet."])
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend([f"- {item['claim']}: {item['reason']}" for item in blocked] or ["- None."])
    lines.extend(["", "## Next Action", "", f"- {next_actions[0] if next_actions else 'No next action selected.'}", ""])

    claims = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "allowed_claims": allowed,
        "blocked_claims": blocked,
        "under_sampled_groups": under_sampled,
        "next_actions": next_actions[:3],
    }
    return claims, "\n".join(lines)


def _plot_uncertainty_dashboard(uncertainty: list[dict[str, object]], path: Path) -> None:
    rows = [row for row in uncertainty if row.get("group_level") == "campaign_family" and int(row.get("arrival_n", 0)) > 0]
    rows = sorted(rows, key=lambda row: (str(row.get("campaign_id")), str(row.get("family"))))
    labels = [f"{row.get('campaign_id')}:{row.get('family')}" for row in rows]
    shown = min(len(rows), 32)
    x = np.arange(shown)
    arrival = np.asarray([float(row.get("arrival_mean", 0.0)) for row in rows[:shown]], dtype=float)
    arrival_low = np.asarray([float(row.get("arrival_ci95_low", 0.0)) for row in rows[:shown]], dtype=float)
    arrival_high = np.asarray([float(row.get("arrival_ci95_high", 0.0)) for row in rows[:shown]], dtype=float)
    gain = np.asarray([float(row.get("gain_mean", 0.0)) for row in rows[:shown]], dtype=float)
    gain_low = np.asarray([float(row.get("gain_ci95_low", 0.0)) for row in rows[:shown]], dtype=float)
    gain_high = np.asarray([float(row.get("gain_ci95_high", 0.0)) for row in rows[:shown]], dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), constrained_layout=True)
    axes[0].errorbar(x, arrival, yerr=[arrival - arrival_low, arrival_high - arrival], fmt="o", capsize=3)
    axes[0].set_title("Target arrival with CI95")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels[:shown], rotation=60, ha="right", fontsize=7)
    axes[0].grid(alpha=0.25)
    axes[1].errorbar(x, gain, yerr=[gain - gain_low, gain_high - gain], fmt="o", capsize=3, color="#c44e52")
    axes[1].axhline(0.05, color="black", linestyle="--", linewidth=1.0, label="strong assistance threshold")
    axes[1].set_title("Dephasing gain with CI95")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels[:shown], rotation=60, ha="right", fontsize=7)
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_evidence_prep_decision_panel(master_results: list[dict[str, object]], path: Path) -> None:
    rows = [row for row in master_results if row.get("campaign_id") == "dynamic_network_atlas_evidence_prep"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "No evidence_prep records yet.\nRun: python scripts/run_transport_dynamic_network_atlas.py --profile evidence_prep",
            ha="center",
            va="center",
            fontsize=12,
        )
        fig.savefig(path, dpi=220)
        plt.close(fig)
        return

    families = sorted({str(row.get("family", "unknown")) for row in rows})
    metrics = [
        ("arrival", "Target arrival"),
        ("gain", "Dephasing gain"),
        ("quantum_minus_classical", "Quantum - classical"),
        ("entropy", "Final entropy"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    for ax, (metric, title) in zip(axes.flat, metrics, strict=False):
        means = []
        lows = []
        highs = []
        for family in families:
            values = [_as_float(row.get(metric)) for row in rows if str(row.get("family")) == family]
            values = [value for value in values if np.isfinite(value)]
            summary = mean_std_sem_ci95(values)
            means.append(float(summary["mean"]))
            lows.append(float(summary["ci95_low"]))
            highs.append(float(summary["ci95_high"]))
        y = np.asarray(means)
        ylow = np.asarray(lows)
        yhigh = np.asarray(highs)
        x = np.arange(len(families))
        ax.errorbar(x, y, yerr=[y - ylow, yhigh - y], fmt="o", capsize=3)
        if metric in {"gain", "quantum_minus_classical"}:
            ax.axhline(0.05, color="black", linestyle="--", linewidth=1)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(families, rotation=45, ha="right", fontsize=8)
        ax.grid(alpha=0.25)
    fig.suptitle("Evidence-prep decision panel", fontsize=16)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def write_transport_lab_memory(manifest: list[dict[str, object]], claims: dict[str, object], path: Path) -> None:
    lines = ["# Transport Lab Memory", "", f"Updated UTC: {datetime.now(UTC).isoformat()}", "", "## Current State", ""]
    for entry in manifest:
        lines.append(
            f"- `{entry['campaign_id']}`: profile `{entry['profile']}`, evidence `{entry['evidence_status']}`, numerics_pass `{entry['numerics_pass']}`."
        )
    lines.extend(["", "## Allowed Claims", ""])
    for item in list(claims.get("allowed_claims", [])):
        lines.append(f"- {item.get('claim')}")
    lines.extend(["", "## Blocked Claims", ""])
    for item in list(claims.get("blocked_claims", [])):
        lines.append(f"- {item.get('claim')}: {item.get('reason')}")
    lines.extend(["", "## Next Actions", ""])
    for action in list(claims.get("next_actions", [])):
        lines.append(f"- {action}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_master_report(manifest: list[dict[str, object]], claims: dict[str, object], metrics: dict[str, object], path: Path) -> None:
    lines = [
        "# Master Scientific Report: Dynamic Open-Quantum Transport Laboratory",
        "",
        "## Hypothesis",
        "",
        "Finite networks leave dynamic fingerprints in open quantum transport. These fingerprints should help distinguish network families and identify when environmental phase scrambling helps or hurts target arrival.",
        "",
        "## Effective Model",
        "",
        "The current model is an effective single-excitation tight-binding network with local disorder, dephasing, loss, and a target arrival channel. It is not a microscopic material model.",
        "",
        "## Numerical Validation",
        "",
        f"- Master result rows: {metrics.get('master_result_count', 0)}",
        f"- Uncertainty rows: {metrics.get('master_uncertainty_count', 0)}",
        f"- Campaigns registered: {len(manifest)}",
        "",
        "## Dynamic Atlas",
        "",
        "The atlas pipeline exists. The current atlas output is marked according to its campaign profile; smoke outputs are not used as scientific conclusions.",
        "",
        "## Target Placement",
        "",
        "Existing target-geometry campaigns support target placement as a central variable, but interactive campaigns remain exploratory unless confirmed by paper/strong profiles.",
        "",
        "## Quantum Vs Classical Control",
        "",
        "Quantum-minus-classical comparisons are aggregated in the master table. A quantum signature is allowed only when the mean difference is above 0.05 and CI95 is positive.",
        "",
        "## Entropy And Mixing Diagnostics",
        "",
        "Entropy, purity, Shannon population entropy, participation ratio and IPR are treated as diagnostics of mixing/spreading, not as direct transport efficiency.",
        "",
        "## Fractal Exploratory Front",
        "",
        "Fractal geometries remain an exploratory geometry front. They can motivate future propagation studies but are not yet a central classification claim.",
        "",
        "## Paper-By-Paper Guardrails",
        "",
        "The paper reproduction suite provides guardrails for claims connected to ENAQT, target placement, open quantum walks, graph similarity and experimental analogies.",
        "",
        "## Allowed Claims",
        "",
    ]
    lines.extend([f"- {item.get('claim')}" for item in list(claims.get("allowed_claims", []))] or ["- None yet."])
    lines.extend(["", "## Limitations", ""])
    lines.extend([f"- {item.get('claim')}: {item.get('reason')}" for item in list(claims.get("blocked_claims", []))] or ["- None listed."])
    lines.extend(["", "## Next Campaign", ""])
    next_actions = list(claims.get("next_actions", []))
    lines.append(f"- {next_actions[0] if next_actions else 'No next action selected.'}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_master_notebook(path: Path) -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Transport Lab Master Notebook\n",
                "\n",
                "Notebook principal do laboratorio. Ele nao roda campanhas automaticamente; carrega o registro mestre e mostra o estado cientifico atual.\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Como ler\n",
                "\n",
                "- `arrival`: quanto chegou ao canal de chegada ao alvo.\n",
                "- `gain`: melhora causada por embaralhamento de fase.\n",
                "- `entropy`: mistura/espalhamento, nao eficiencia.\n",
                "- `quantum_minus_classical`: chegada quantica menos chegada classica no mesmo grafo.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "import csv, json\n",
                "from IPython.display import Image, Markdown, display\n",
                "\n",
                "ROOT = Path.cwd()\n",
                "if not (ROOT / 'pyproject.toml').exists():\n",
                "    ROOT = ROOT.parent\n",
                "REG = ROOT / 'outputs' / 'transport_networks' / 'lab_registry' / 'latest'\n",
                "REPORT = ROOT / 'outputs' / 'transport_networks' / 'master_scientific_report' / 'latest'\n",
                "REG\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "manifest = json.loads((REG / 'campaign_manifest.json').read_text(encoding='utf-8'))\n",
                "claims = json.loads((REG / 'master_claims.json').read_text(encoding='utf-8'))\n",
                "display(manifest)\n",
                "display(claims['next_actions'])\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "with (REG / 'master_uncertainty.csv').open('r', encoding='utf-8', newline='') as handle:\n",
                "    uncertainty = list(csv.DictReader(handle))\n",
                "rows = [row for row in uncertainty if row['group_level'] == 'campaign_family']\n",
                "rows[:10]\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "fig = REG / 'figures' / 'uncertainty_dashboard.png'\n",
                "if fig.exists():\n",
                "    display(Image(filename=str(fig)))\n",
                "else:\n",
                "    print('Figure missing:', fig)\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Campanha de preparacao no PC atual\n",
                "\n",
                "Esta secao resume `dynamic_network_atlas_evidence_prep`: uma campanha moderada, nao-smoke, focada em familias candidatas. Ela serve para decidir o que merece o atlas completo no Mac.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "prep_fig = REG / 'figures' / 'evidence_prep_decision_panel.png'\n",
                "if prep_fig.exists():\n",
                "    display(Image(filename=str(prep_fig)))\n",
                "else:\n",
                "    print('Figure missing:', prep_fig)\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Claims finais\n",
                "\n",
                "Leia `master_critic_report.md` antes de qualquer conclusao forte. Se o critic bloqueou, a conclusao nao deve ir para proposta/artigo ainda.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(Markdown((REG / 'master_critic_report.md').read_text(encoding='utf-8')))\n",
                "display(Markdown((REPORT / 'master_report.md').read_text(encoding='utf-8')))\n",
            ],
        },
    ]
    payload = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")


def build_registry_outputs() -> dict[str, object]:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_campaign_manifest()
    master_results = build_master_results(manifest)
    uncertainty = build_uncertainty(master_results)
    claims, critic_text = build_claims_and_critic(manifest, uncertainty)

    (REGISTRY_DIR / "campaign_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_csv(master_results, REGISTRY_DIR / "master_results.csv")
    _write_csv(uncertainty, REGISTRY_DIR / "master_uncertainty.csv")
    (REGISTRY_DIR / "master_claims.json").write_text(json.dumps(claims, indent=2), encoding="utf-8")
    (REGISTRY_DIR / "master_critic_report.md").write_text(critic_text + "\n", encoding="utf-8")
    _plot_uncertainty_dashboard(uncertainty, REGISTRY_DIR / "figures" / "uncertainty_dashboard.png")
    _plot_evidence_prep_decision_panel(master_results, REGISTRY_DIR / "figures" / "evidence_prep_decision_panel.png")

    metrics = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "campaign_count": len(manifest),
        "master_result_count": len(master_results),
        "master_uncertainty_count": len(uncertainty),
        "smoke_only_campaigns": [entry["campaign_id"] for entry in manifest if entry["evidence_status"] == "smoke_only"],
        "scientific_candidate_campaigns": [entry["campaign_id"] for entry in manifest if entry["evidence_status"] == "scientific_candidate"],
        "allowed_claim_count": len(claims.get("allowed_claims", [])),
        "blocked_claim_count": len(claims.get("blocked_claims", [])),
    }
    (REGISTRY_DIR / "master_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_transport_lab_memory(manifest, claims, REGISTRY_DIR / "transport_lab_memory.md")
    write_master_report(manifest, claims, metrics, REPORT_DIR / "master_report.md")
    write_master_notebook(NOTEBOOK_PATH)
    return metrics


def run_atlas_strong() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_transport_dynamic_network_atlas.py"), "--profile", "strong"],
        cwd=ROOT,
        check=True,
    )


def run_atlas_intense() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_transport_dynamic_network_atlas.py"), "--profile", "intense"],
        cwd=ROOT,
        check=True,
    )


def run_atlas_evidence_prep() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_transport_dynamic_network_atlas.py"), "--profile", "evidence_prep"],
        cwd=ROOT,
        check=True,
    )


def run_pipeline(mode: str) -> dict[str, object]:
    if mode == "registry_only":
        return build_registry_outputs()
    if mode == "evidence_prep":
        run_atlas_evidence_prep()
        return build_registry_outputs()
    if mode == "atlas_strong":
        run_atlas_strong()
        return build_registry_outputs()
    if mode == "atlas_intense":
        run_atlas_intense()
        return build_registry_outputs()
    if mode == "validation_pack":
        return build_registry_outputs()
    if mode == "notebook_report_pack":
        return build_registry_outputs()
    if mode == "all":
        run_atlas_strong()
        return build_registry_outputs()
    raise ValueError(f"unsupported mode: {mode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the master evidence layer for the transport lab.")
    parser.add_argument(
        "--mode",
        choices=["registry_only", "evidence_prep", "atlas_strong", "atlas_intense", "validation_pack", "notebook_report_pack", "all"],
        default="registry_only",
    )
    args = parser.parse_args()
    metrics = run_pipeline(args.mode)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
