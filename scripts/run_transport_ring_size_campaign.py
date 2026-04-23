from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

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

from oqs_transport import best_by_disorder, write_literature_guardrails, write_summary_markdown  # noqa: E402


SEEDS_12 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
LITERATURE_GUARDRAILS = [
    {"key": "PlenioHuelga2008", "url": "https://doi.org/10.1088/1367-2630/10/11/113019", "reading": "Noise assistance depends on network symmetry and destructive interference."},
    {"key": "Razzoli2021", "url": "https://doi.org/10.3390/e23010085", "reading": "Trap position and graph structure jointly determine transport efficiency."},
    {"key": "MuelkenBlumen2011", "url": "https://doi.org/10.1016/j.physrep.2011.01.002", "reading": "Continuous-time quantum transport on networks can change qualitatively with topology and size."},
]


def build_ring_size_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "If the target-position effect is structural, the unfavorable target should keep a positive average gain across several ring sizes.",
        "expected_role_of_disorder": "Strong disorder should lower the absolute arrival but should not erase the size trend completely if the effect is robust.",
        "expected_role_of_phase_scrambling": "Moderate phase scrambling should help mainly the unfavorable target if interference is the main blocking mechanism.",
        "expected_failure_mode": "If only one size shows assistance, the effect is likely finite-size-sensitive.",
    }
    scenarios: list[dict[str, object]] = []
    for n_sites in [6, 8, 10, 12]:
        for label, trap_site in [("favorable", 0), ("unfavorable", 1)]:
            scenarios.append(
                {
                    "name": f"Ring size N{n_sites} {label} target",
                    "coupling_hz": 1.0,
                    "sink_rate_hz": 0.65,
                    "loss_rate_hz": 0.02,
                    "initial_site": n_sites // 2,
                    "trap_site": trap_site,
                    "medium": {
                        "medium_type": "ring",
                        "n_sites": n_sites,
                        "length_scale": 1.0,
                        "coupling_law": "nearest_neighbor",
                        "site_energy_profile": "static_disorder",
                        "sink_definition": {"mode": "single_site", "site_index": trap_site},
                        "loss_definition": {"mode": "uniform_local_loss"},
                        "interface_axis": "x",
                        "interface_position": 0.0,
                    },
                    "literature_expectation": expectation,
                }
            )
    return {
        "study_name": "Ring size and symmetry campaign",
        "output_subdir": "medium_ring_size",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.6, 0.8, 1.0, 1.2],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2],
        },
        "ensemble_seeds": SEEDS_12,
        "scenarios": scenarios,
    }


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "medium_ring_size" / "latest" / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_size_and_label(name: str) -> tuple[int, str]:
    parts = name.split()
    size_token = next(part for part in parts if part.startswith("N"))
    # "unfavorable" contains "favorable", so test the longer label first.
    label = "unfavorable" if "unfavorable" in name.lower() else "favorable"
    return int(size_token[1:]), label


def _aggregate(results_payload: dict[str, object]) -> dict[str, dict[str, list[float]]]:
    buckets: dict[str, dict[str, list[float]]] = {
        "favorable": {"size": [], "best_arrival": [], "gain": [], "best_phase": [], "spread": []},
        "unfavorable": {"size": [], "best_arrival": [], "gain": [], "best_phase": [], "spread": []},
    }
    grouped: dict[tuple[int, str], dict[str, float]] = {}
    for scenario in results_payload["scenarios"]:
        size, label = _parse_size_and_label(str(scenario["scenario_name"]))
        derived = best_by_disorder(scenario)
        grouped[(size, label)] = {
            "best_arrival": float(np.mean(derived["best"])),
            "gain": float(np.mean(derived["gain"])),
            "best_phase": float(np.mean(derived["best_dephasing"])),
            "spread": float(np.mean(derived["best_std"])),
        }
    for label in ["favorable", "unfavorable"]:
        for size in [6, 8, 10, 12]:
            row = grouped[(size, label)]
            buckets[label]["size"].append(float(size))
            for key in ["best_arrival", "gain", "best_phase", "spread"]:
                buckets[label][key].append(float(row[key]))
    return buckets


def _plot_dashboard(results_payload: dict[str, object], output_path: Path) -> None:
    agg = _aggregate(results_payload)
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.0), constrained_layout=True)
    colors = {"favorable": "#2563eb", "unfavorable": "#dc2626"}
    for label in ["favorable", "unfavorable"]:
        x = agg[label]["size"]
        axes[0, 0].plot(x, agg[label]["best_arrival"], marker="o", lw=2.4, color=colors[label], label=label)
        axes[0, 1].plot(x, agg[label]["gain"], marker="o", lw=2.4, color=colors[label], label=label)
        axes[1, 0].plot(x, agg[label]["best_phase"], marker="o", lw=2.4, color=colors[label], label=label)
        axes[1, 1].plot(x, agg[label]["spread"], marker="o", lw=2.4, color=colors[label], label=label)
    axes[0, 0].set_title("best arrival versus ring size")
    axes[0, 0].set_ylabel("mean best arrival across disorder scan")
    axes[0, 1].set_title("mean gain versus ring size")
    axes[0, 1].set_ylabel("mean gain over zero scrambling")
    axes[1, 0].set_title("mean best phase-scrambling versus ring size")
    axes[1, 0].set_ylabel("mean best relative rate")
    axes[1, 1].set_title("mean ensemble spread versus ring size")
    axes[1, 1].set_ylabel("mean standard deviation")
    for axis in axes.ravel():
        axis.set_xlabel("number of sites N")
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    fig.suptitle("Ring size and symmetry campaign", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(results_payload: dict[str, object], output_path: Path) -> None:
    sizes = [6, 8, 10, 12]
    disorders = [0.6, 0.8, 1.0, 1.2]
    labels = ["favorable", "unfavorable"]
    gain_grids = {label: np.zeros((len(sizes), len(disorders)), dtype=float) for label in labels}
    for scenario in results_payload["scenarios"]:
        size, label = _parse_size_and_label(str(scenario["scenario_name"]))
        derived = best_by_disorder(scenario)
        for idx, disorder_value in enumerate(derived["disorder"]):
            gain_grids[label][sizes.index(size), idx] = float(derived["gain"][idx])
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), constrained_layout=True)
    for axis, label in zip(axes, labels, strict=True):
        image = axis.imshow(gain_grids[label], origin="lower", aspect="auto", cmap="viridis")
        axis.set_title(f"{label} target: mean gain")
        axis.set_xticks(np.arange(len(disorders)))
        axis.set_xticklabels([f"{value:.1f}" for value in disorders])
        axis.set_yticks(np.arange(len(sizes)))
        axis.set_yticklabels([str(size) for size in sizes])
        axis.set_xlabel("local irregularity / coherent coupling")
        axis.set_ylabel("ring size N")
        fig.colorbar(image, ax=axis, shrink=0.85, label="best arrival minus zero-scrambling arrival")
    fig.suptitle("Ring size gain heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(results_payload: dict[str, object], output_dir: Path) -> None:
    agg = _aggregate(results_payload)
    favorable_gain = np.asarray(agg["favorable"]["gain"], dtype=float)
    unfavorable_gain = np.asarray(agg["unfavorable"]["gain"], dtype=float)
    positive_across_sizes = bool(np.all(unfavorable_gain > 0.02))
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    table_headers = ["target type", "N", "mean best arrival", "mean gain", "mean best phase", "mean spread"]
    table_rows: list[list[str]] = []
    for label in ["favorable", "unfavorable"]:
        for size, best_arrival, gain, phase, spread in zip(
            agg[label]["size"],
            agg[label]["best_arrival"],
            agg[label]["gain"],
            agg[label]["best_phase"],
            agg[label]["spread"],
            strict=True,
        ):
            table_rows.append([label, f"{int(size)}", f"{best_arrival:.3f}", f"{gain:.3f}", f"{phase:.3f}", f"{spread:.3f}"])
    write_summary_markdown(
        output_dir / "summary.md",
        title="Ring size and symmetry campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[
            f"Generated at UTC: {datetime.now(UTC).isoformat()}",
            "Goal: check whether the favorable/unfavorable target contrast survives changes in ring size.",
        ],
        measured_lines=[
            f"Mean unfavorable-target gain across sizes ranges from {float(np.min(unfavorable_gain)):.3f} to {float(np.max(unfavorable_gain)):.3f}.",
            f"Mean favorable-target gain across sizes ranges from {float(np.min(favorable_gain)):.3f} to {float(np.max(favorable_gain)):.3f}.",
            f"Unfavorable target positive-across-sizes status: {'yes' if positive_across_sizes else 'no'}.",
        ],
        agreement_lines=[
            "This agrees with the literature if the unfavorable target keeps a positive gain while the favorable target stays near the coherent optimum.",
            "If both target types behave the same after averaging over disorder, the target-position effect is not structurally robust.",
        ],
        uncertainty_lines=[
            "These are disorder-averaged summaries, so finer structure at individual disorder values is compressed into one line per size.",
            "This campaign uses 12 seeds and is appropriate for interactive review, not the last confirmatory step.",
        ],
        table_headers=table_headers,
        table_rows=table_rows,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ring size and symmetry campaign.")
    parser.add_argument("--skip-simulation", action="store_true", help="Reuse existing results and rebuild dashboards only.")
    parser.add_argument("--skip-visuals", action="store_true", help="Do not regenerate selected Journey 1 visuals.")
    args = parser.parse_args(argv)

    config = build_ring_size_config()
    config_path = ROOT / "configs" / "transport_ring_size_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_ring_size" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    if not args.skip_visuals:
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_transport_visual_journey1.py"),
                "--config",
                str(config_path),
                "--results",
                str(results_path),
                "--scenario-name",
                "Ring size N8 favorable target",
                "--scenario-name",
                "Ring size N8 unfavorable target",
                "--scenario-name",
                "Ring size N12 unfavorable target",
            ]
        )
    results_payload = _load_results()
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_ring_size" / "latest" / "campaign_review"
    _plot_dashboard(results_payload, review_dir / "ring_size_dashboard.png")
    _plot_heatmap(results_payload, review_dir / "ring_size_heatmap.png")
    _write_summary(results_payload, review_dir)
    (review_dir / "run_metadata.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
