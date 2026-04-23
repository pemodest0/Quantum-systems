from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()


FIGURES = [
    ("closed_walk_benchmark.png", "Closed coherent benchmark", "Control without target loss, dephasing, or disorder. Different curves mean topology is visible in the dynamics."),
    ("target_placement_with_controls.png", "Target placement", "Shows how changing only the successful-arrival node changes transport."),
    ("dephasing_gain_with_ci.png", "Dephasing gain with uncertainty", "Positive bars mean phase scrambling improved target arrival relative to zero dephasing."),
    ("quantum_vs_classical_arrival.png", "Quantum/open versus classical", "Points above the diagonal mean the quantum/open model arrived better than the classical rate control."),
    ("classification_group_vs_row.png", "Classification honesty check", "Compares optimistic row split against honest graph-instance group split."),
    ("size_generalization.png", "Size generalization", "Trains at N=8 and tests at larger N when available."),
]


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_pack(campaign_dir: Path) -> Path:
    metrics = _load_json(campaign_dir / "metrics.json")
    paper = _load_json(campaign_dir / "paper_reproduction_score.json")
    paper_suite = _load_json(ROOT / "outputs" / "transport_networks" / "paper_reproduction_suite" / "latest" / "paper_verdicts.json")
    strongest = metrics.get("strongest_statistical_gain", {})
    if isinstance(strongest, dict) and strongest:
        next_candidate = (
            f"`{strongest.get('family', 'unknown')} + {strongest.get('edge_model', 'unknown')} + "
            f"{strongest.get('target_style', 'unknown')} target`"
        )
    else:
        next_candidate = "`strongest measured candidate`"
    figures_dir = campaign_dir / "figures"
    output_path = campaign_dir / "scientific_findings_pack.md"
    lines = [
        "# Scientific Findings Pack",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        f"Campaign: `{campaign_dir}`",
        "",
        "## Executive Reading",
        "",
        f"- Verdict: `{metrics.get('scientific_verdict', 'unknown')}`.",
        f"- Open signatures: {metrics.get('open_signature_count', 'unknown')}.",
        f"- Group split combined accuracy: {float(metrics.get('group_combined_accuracy', 0.0)):.3f}.",
        f"- Group split baseline: {float(metrics.get('group_baseline_accuracy', 0.0)):.3f}.",
        f"- Classical-only group accuracy: {float(metrics.get('group_classical_accuracy', 0.0)):.3f}.",
        f"- Strongest mean dephasing gain: {float(metrics.get('max_gain_mean', 0.0)):.3f}.",
        f"- Numerics pass: {metrics.get('numerics_pass', False)}.",
        "",
        "## Paper Guardrails",
        "",
        f"- Matched: {paper.get('matched_expectation', [])}.",
        f"- Failed: {paper.get('failed_expectation', [])}.",
        f"- Uncertain: {paper.get('uncertain', [])}.",
        "",
    ]
    if paper_suite:
        lines.extend(
            [
                "## Paper-By-Paper Reproduction Status",
                "",
                "| Paper | Verdict | Claims | Mean confidence |",
                "|---|---:|---:|---:|",
            ]
        )
        for paper_key, payload in sorted(paper_suite.items()):
            if not isinstance(payload, dict):
                continue
            lines.append(
                f"| `{paper_key}` | `{payload.get('verdict', 'unknown')}` | "
                f"{payload.get('claim_count', 0)} | {float(payload.get('mean_confidence', 0.0)):.2f} |"
            )
        lines.append("")
    lines.extend(["## Figures", ""])
    for filename, title, description in FIGURES:
        figure_path = figures_dir / filename
        if not figure_path.exists():
            continue
        lines.extend(
            [
                f"### {title}",
                "",
                description,
                "",
                f"![{title}](figures/{filename})",
                "",
            ]
        )
    lines.extend(
        [
            "## Next Action",
            "",
            f"Run a focused confirm/refinement campaign for {next_candidate}. Do not expand to new physics layers before this validation step.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a compact Markdown findings pack from a scientific validation campaign.")
    parser.add_argument("--campaign-dir", default=str(ROOT / "outputs" / "transport_networks" / "scientific_validation" / "latest"))
    args = parser.parse_args(argv)
    output_path = build_pack(Path(args.campaign_dir).resolve())
    print(json.dumps({"findings_pack": str(output_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
