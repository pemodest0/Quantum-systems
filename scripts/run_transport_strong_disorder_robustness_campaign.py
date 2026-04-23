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


SEEDS_16 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
PILOT_SEEDS = [3, 5, 7, 11, 13, 17]
LITERATURE_GUARDRAILS = [
    {"key": "Novo2016", "url": "https://doi.org/10.1038/srep18142", "reading": "Robustness claims must be checked with disorder ensembles, not from single draws."},
    {"key": "Coutinho2022", "url": "https://doi.org/10.1038/s42005-022-00866-7", "reading": "Network robustness under noise requires both mean performance and variability."},
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Moderate dephasing can partially recover transport once disorder is significant."},
]


def build_strong_disorder_robustness_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "Under strong disorder, different media should separate more clearly in both mean arrival and ensemble spread.",
        "expected_role_of_disorder": "The strongest tested disorder values should depress arrival and expose which medium is truly robust.",
        "expected_role_of_phase_scrambling": "A medium that benefits from moderate scrambling under strong disorder is a better candidate for robust assisted transport.",
        "expected_failure_mode": "Ranking by mean only is unsafe if ensemble spread is large enough to erase the differences.",
    }
    scenarios = [
        {
            "name": "Strong disorder chain",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 9,
            "trap_site": 0,
            "medium": {
                "medium_type": "chain_1d",
                "n_sites": 10,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 4.5,
            },
            "literature_expectation": expectation,
        },
        {
            "name": "Strong disorder ring",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 4,
            "trap_site": 0,
            "medium": {
                "medium_type": "ring",
                "n_sites": 8,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 0.0,
            },
            "literature_expectation": expectation,
        },
        {
            "name": "Strong disorder 2D square",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 15,
            "trap_site": 0,
            "medium": {
                "medium_type": "square_lattice_2d",
                "n_rows": 4,
                "n_cols": 4,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 1.5,
            },
            "literature_expectation": expectation,
        },
    ]
    return {
        "study_name": "Strong-disorder robustness campaign",
        "output_subdir": "medium_strong_disorder_robustness",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.8, 1.0, 1.2, 1.4],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
        },
        "ensemble_seeds": SEEDS_16,
        "scenarios": scenarios,
    }


def _apply_pilot_mode(config: dict[str, object]) -> None:
    config["runtime_mode"] = "interactive_pilot"
    config["pilot_note"] = "Reduced seeds and phase-scrambling grid for interactive review; use without --pilot for the 16-seed confirmatory run."
    config["ensemble_seeds"] = PILOT_SEEDS
    config["time_grid"] = {"t_final": 18.0, "n_samples": 160}
    sweep = dict(config["sweep"])
    sweep["dephasing_over_coupling"] = [0.0, 0.1, 0.4, 0.8]
    config["sweep"] = sweep


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results() -> dict[str, object]:
    return json.loads((ROOT / "outputs" / "transport_networks" / "medium_strong_disorder_robustness" / "latest" / "results.json").read_text(encoding="utf-8"))


def _aggregate(results_payload: dict[str, object]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for scenario in results_payload["scenarios"]:
        derived = best_by_disorder(scenario)
        rows.append(
            {
                "scenario": str(scenario["scenario_name"]).replace("Strong disorder ", ""),
                "arrival": float(np.mean(derived["best"])),
                "spread": float(np.mean(derived["best_std"])),
                "phase": float(np.mean(derived["best_dephasing"])),
                "gain": float(np.mean(derived["gain"])),
            }
        )
    return rows


def _plot_dashboard(rows: list[dict[str, float | str]], output_path: Path) -> None:
    labels = [str(row["scenario"]) for row in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.8), constrained_layout=True)
    axes[0].bar(x, [float(row["arrival"]) for row in rows], color="#2563eb")
    axes[0].set_title("best arrival under strong disorder")
    axes[0].set_ylabel("mean best arrival")
    axes[1].bar(x, [float(row["spread"]) for row in rows], color="#dc2626")
    axes[1].set_title("ensemble spread under strong disorder")
    axes[1].set_ylabel("mean standard deviation")
    axes[2].bar(x, [float(row["phase"]) for row in rows], color="#16a34a")
    axes[2].set_title("best phase-scrambling under strong disorder")
    axes[2].set_ylabel("mean best relative rate")
    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=20, ha="right")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Strong-disorder robustness comparison", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(results_payload: dict[str, object], output_path: Path) -> None:
    rows = _aggregate(results_payload)
    disorders = np.asarray([0.8, 1.0, 1.2, 1.4], dtype=float)
    mediums = [str(row["scenario"]) for row in rows]
    arrival_grid = np.zeros((len(mediums), len(disorders)), dtype=float)
    phase_grid = np.zeros((len(mediums), len(disorders)), dtype=float)
    for medium_index, scenario in enumerate(results_payload["scenarios"]):
        derived = best_by_disorder(scenario)
        arrival_grid[medium_index, :] = derived["best"]
        phase_grid[medium_index, :] = derived["best_dephasing"]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    im0 = axes[0].imshow(arrival_grid, origin="lower", aspect="auto", cmap="viridis")
    im1 = axes[1].imshow(phase_grid, origin="lower", aspect="auto", cmap="plasma")
    axes[0].set_title("best arrival")
    axes[1].set_title("best phase-scrambling")
    for axis in axes:
        axis.set_xticks(np.arange(len(disorders)))
        axis.set_xticklabels([f"{value:.1f}" for value in disorders])
        axis.set_yticks(np.arange(len(mediums)))
        axis.set_yticklabels(mediums)
        axis.set_xlabel("local irregularity / coherent coupling")
        axis.set_ylabel("medium")
    fig.colorbar(im0, ax=axes[0], shrink=0.85, label="final target population")
    fig.colorbar(im1, ax=axes[1], shrink=0.85, label="best relative phase-scrambling rate")
    fig.suptitle("Strong-disorder robustness heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(rows: list[dict[str, float | str]], output_dir: Path) -> None:
    best_by_mean = max(rows, key=lambda item: float(item["arrival"]))
    best_by_spread = min(rows, key=lambda item: float(item["spread"]))
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="Strong-disorder robustness campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[f"Generated at UTC: {datetime.now(UTC).isoformat()}", "Goal: compare chain, ring and 2D square under genuinely difficult disorder values using both mean arrival and ensemble spread."],
        measured_lines=[f"Best mean arrival: {best_by_mean['scenario']} with {float(best_by_mean['arrival']):.3f}.", f"Best robustness by spread: {best_by_spread['scenario']} with spread {float(best_by_spread['spread']):.3f}."],
        agreement_lines=["This agrees with the literature only if the ranking by mean is reported together with the ranking by spread.", "If the same medium wins both by mean and by spread, the robustness claim is materially stronger."],
        uncertainty_lines=["A medium should not be called best from mean arrival alone if the ensemble spread is comparable to the mean separation.", "This is still an interactive campaign with 16 seeds, not the heaviest confirmatory run."],
        table_headers=["medium", "mean best arrival", "mean spread", "mean best phase", "mean gain"],
        table_rows=[[str(row["scenario"]), f"{float(row['arrival']):.3f}", f"{float(row['spread']):.3f}", f"{float(row['phase']):.3f}", f"{float(row['gain']):.3f}"] for row in rows],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the strong-disorder robustness comparison.")
    parser.add_argument("--skip-simulation", action="store_true")
    parser.add_argument("--skip-visuals", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Run the lighter interactive pilot grid.")
    args = parser.parse_args(argv)

    config = build_strong_disorder_robustness_config()
    if args.pilot:
        _apply_pilot_mode(config)
    config_path = ROOT / "configs" / "transport_strong_disorder_robustness_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_strong_disorder_robustness" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    results_payload = _load_results()
    if not args.skip_visuals:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_transport_visual_journey1.py"),
            "--config",
            str(config_path),
            "--results",
            str(results_path),
            "--scenario-name",
            "Strong disorder chain",
            "--scenario-name",
            "Strong disorder ring",
            "--scenario-name",
            "Strong disorder 2D square",
        ]
        _run(command)
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_strong_disorder_robustness" / "latest" / "campaign_review"
    rows = _aggregate(results_payload)
    _plot_dashboard(rows, review_dir / "strong_disorder_dashboard.png")
    _plot_heatmap(results_payload, review_dir / "strong_disorder_heatmaps.png")
    _write_summary(rows, review_dir)
    (review_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
