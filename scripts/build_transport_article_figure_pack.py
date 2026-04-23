from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _image_or_blank(ax, path: Path, title: str) -> None:
    ax.set_title(title, fontsize=10)
    ax.axis("off")
    if path.exists():
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, f"Missing\n{path.name}", ha="center", va="center")


def build_pack(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    journey = ROOT / "outputs" / "transport_networks" / "research_journey_v2" / "latest"
    target = ROOT / "outputs" / "transport_networks" / "target_geometry_confirm" / "latest"
    fractal = ROOT / "outputs" / "transport_networks" / "fractal_geometry_followup" / "latest"
    classification = ROOT / "outputs" / "transport_networks" / "network_classification_complete" / "latest"

    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.0), constrained_layout=True)
    _image_or_blank(axes[0, 0], target / "figures" / "target_pair_contrasts.png", "A. Target placement")
    _image_or_blank(axes[0, 1], target / "figures" / "quantum_classical_target_controls.png", "B. Quantum/open vs classical")
    _image_or_blank(axes[1, 0], classification / "figures" / "accuracy_by_feature_set.png", "C. Network classification")
    _image_or_blank(axes[1, 1], fractal / "figures" / "fractal_vs_lattice_msd.png", "D. Fractal spreading")
    figure_path = figures_dir / "article_four_panel.png"
    fig.savefig(figure_path, dpi=220)
    plt.close(fig)

    journey_metrics = _load_json(journey / "metrics.json")
    target_metrics = _load_json(target / "metrics.json")
    fractal_metrics = _load_json(fractal / "metrics.json")
    classification_metrics = _load_json(classification / "metrics.json")
    lines = [
        "# Article Figure Pack Claims",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        "",
        "## Allowed Claims",
        "",
        f"- Target placement has a confirmed effect in `{target_metrics.get('confirmed_family_count', 0)}` focused families if CI95 lower bound exceeds `0.05`.",
        f"- Open-quantum transport differs from the classical rate-walk control in `{target_metrics.get('quantum_advantage_like_count', 0)}` target-control cases.",
        f"- Existing classification result: combined dynamic+topological features reach `{float(classification_metrics.get('combined_accuracy', 0.0)):.3f}` accuracy versus baseline `{float(classification_metrics.get('combined_baseline', 0.0)):.3f}`.",
        f"- Fractal follow-up verdict: `{fractal_metrics.get('fractal_geometry_changes_spreading', False)}`.",
        "",
        "## Claims Not Yet Allowed",
        "",
        "- Do not claim microscopic simulation of photosynthesis, perovskites, or superconducting hardware.",
        "- Do not claim graph-family classification from dynamics alone is complete; topology plus dynamics remains stronger.",
        "- Do not claim fractals are part of the main classifier until they are added to the classification campaign.",
        "",
        "## Figure",
        "",
        "![Article four panel](figures/article_four_panel.png)",
        "",
        "## Source Metrics",
        "",
        f"- Journey V2 target spread mean: `{journey_metrics.get('target_spread_mean', 'missing')}`.",
        f"- Target confirmation numerics pass: `{target_metrics.get('numerics_pass', False)}`.",
        f"- Fractal numerics pass: `{fractal_metrics.get('numerics_pass', False)}`.",
    ]
    (output_dir / "article_claims.md").write_text("\n".join(lines), encoding="utf-8")
    metrics = {
        "figure": str(figure_path),
        "target_metrics_available": bool(target_metrics),
        "fractal_metrics_available": bool(fractal_metrics),
        "classification_metrics_available": bool(classification_metrics),
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build four-panel article figure pack for transport research.")
    parser.add_argument("--output-subdir", default="article_figure_pack")
    args = parser.parse_args(argv)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = build_pack(output_dir)
    print(json.dumps({"output_dir": str(output_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
