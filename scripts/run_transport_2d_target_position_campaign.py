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

from oqs_transport import best_by_disorder, selected_scenario_names, write_literature_guardrails, write_summary_markdown  # noqa: E402


SEEDS_16 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
PILOT_SEEDS = [3, 5, 7, 11, 13, 17]
LITERATURE_GUARDRAILS = [
    {"key": "Razzoli2021", "url": "https://doi.org/10.3390/e23010085", "reading": "Target position is a first-order control variable for graph transport efficiency."},
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Assistance by the environment is expected mainly when the coherent baseline is frustrated."},
    {"key": "Coutinho2022", "url": "https://doi.org/10.1038/s42005-022-00866-7", "reading": "Robustness and geometry must be evaluated together, not from one best-case number."},
]


def build_2d_target_position_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "A 2D medium should still care about where the target sits, because the target changes path competition and path length.",
        "expected_role_of_disorder": "Higher disorder should lower absolute arrival and can amplify the differences between target choices.",
        "expected_role_of_phase_scrambling": "Targets that are coherent-friendly should stay near the zero-scrambling optimum, while harder targets can shift to a nonzero optimum.",
        "expected_failure_mode": "If all targets become equivalent, geometry of the target is not surviving in this medium.",
    }
    targets = [(0, "corner"), (3, "edge"), (5, "interior"), (10, "far interior")]
    scenarios = []
    for trap_site, label in targets:
        scenarios.append(
            {
                "name": f"2D target {label} trap {trap_site}",
                "coupling_hz": 1.0,
                "sink_rate_hz": 0.65,
                "loss_rate_hz": 0.02,
                "initial_site": 15,
                "trap_site": trap_site,
                "medium": {
                    "medium_type": "square_lattice_2d",
                    "n_rows": 4,
                    "n_cols": 4,
                    "length_scale": 1.0,
                    "coupling_law": "nearest_neighbor",
                    "site_energy_profile": "static_disorder",
                    "sink_definition": {"mode": "single_site", "site_index": trap_site},
                    "loss_definition": {"mode": "uniform_local_loss"},
                    "interface_axis": "x",
                    "interface_position": 1.5,
                },
                "literature_expectation": expectation,
            }
        )
    return {
        "study_name": "2D target-position campaign",
        "output_subdir": "medium_2d_target_position",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.4, 0.6, 0.8, 1.0],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8],
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
    return json.loads((ROOT / "outputs" / "transport_networks" / "medium_2d_target_position" / "latest" / "results.json").read_text(encoding="utf-8"))


def _trap_from_name(name: str) -> int:
    return int(name.split()[-1])


def _aggregate(results_payload: dict[str, object]) -> dict[str, np.ndarray]:
    disorders = [0.4, 0.6, 0.8, 1.0]
    traps = [0, 3, 5, 10]
    best_arrival = np.zeros((len(traps), len(disorders)), dtype=float)
    best_phase = np.zeros((len(traps), len(disorders)), dtype=float)
    ranking_mean = np.zeros(len(traps), dtype=float)
    for scenario in results_payload["scenarios"]:
        trap = _trap_from_name(str(scenario["scenario_name"]))
        derived = best_by_disorder(scenario)
        best_arrival[traps.index(trap), :] = derived["best"]
        best_phase[traps.index(trap), :] = derived["best_dephasing"]
        ranking_mean[traps.index(trap)] = float(np.mean(derived["best"]))
    return {"disorders": np.asarray(disorders, dtype=float), "traps": np.asarray(traps, dtype=int), "best_arrival": best_arrival, "best_phase": best_phase, "ranking_mean": ranking_mean}


def _plot_dashboard(results_payload: dict[str, object], output_path: Path) -> None:
    agg = _aggregate(results_payload)
    order = np.argsort(agg["ranking_mean"])[::-1]
    labels = [f"trap {int(agg['traps'][idx])}" for idx in order]
    values = agg["ranking_mean"][order]
    fig, axis = plt.subplots(figsize=(10.0, 4.8), constrained_layout=True)
    axis.bar(labels, values, color="#0f766e")
    axis.set_ylabel("mean best arrival across disorder scan")
    axis.set_title("2D target ranking by useful arrival")
    axis.grid(axis="y", alpha=0.25)
    fig.suptitle("2D target-position ranking", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(agg: dict[str, np.ndarray], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    im0 = axes[0].imshow(agg["best_arrival"], origin="lower", aspect="auto", cmap="viridis")
    im1 = axes[1].imshow(agg["best_phase"], origin="lower", aspect="auto", cmap="plasma")
    axes[0].set_title("best arrival")
    axes[1].set_title("best phase-scrambling")
    for axis in axes:
        axis.set_xticks(np.arange(len(agg["disorders"])))
        axis.set_xticklabels([f"{value:.1f}" for value in agg["disorders"]])
        axis.set_yticks(np.arange(len(agg["traps"])))
        axis.set_yticklabels([str(int(value)) for value in agg["traps"]])
        axis.set_xlabel("local irregularity / coherent coupling")
        axis.set_ylabel("target index")
    fig.colorbar(im0, ax=axes[0], shrink=0.85, label="final target population")
    fig.colorbar(im1, ax=axes[1], shrink=0.85, label="best relative phase-scrambling rate")
    fig.suptitle("2D target-position heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(results_payload: dict[str, object], output_dir: Path) -> None:
    agg = _aggregate(results_payload)
    order = np.argsort(agg["ranking_mean"])[::-1]
    top_trap = int(agg["traps"][order[0]])
    bottom_trap = int(agg["traps"][order[-1]])
    table_headers = ["target index", "disorder", "best arrival", "best phase scrambling"]
    table_rows = []
    for trap_index, trap in enumerate(agg["traps"]):
        for disorder_index, disorder_value in enumerate(agg["disorders"]):
            table_rows.append([str(int(trap)), f"{float(disorder_value):.2f}", f"{float(agg['best_arrival'][trap_index, disorder_index]):.3f}", f"{float(agg['best_phase'][trap_index, disorder_index]):.3f}"])
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="2D target-position campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[f"Generated at UTC: {datetime.now(UTC).isoformat()}", "Goal: test whether target placement stays important in a 2D medium."],
        measured_lines=[f"Best-ranked target: trap {top_trap}. Worst-ranked target: trap {bottom_trap}.", f"Ranking gap between best and worst targets: {float(agg['ranking_mean'][order[0]] - agg['ranking_mean'][order[-1]]):.3f}."],
        agreement_lines=["This agrees with the literature if different target geometries remain distinguishable in the 2D medium.", "If the best phase-scrambling values differ between targets, geometry is not being washed out by dimensionality."],
        uncertainty_lines=["This is still an effective 2D medium, not a microscopic material model.", "A ranking based on disorder-averaged best arrival compresses details that may still matter row by row."],
        table_headers=table_headers,
        table_rows=table_rows,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 2D target-position campaign.")
    parser.add_argument("--skip-simulation", action="store_true")
    parser.add_argument("--skip-visuals", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Run the lighter interactive pilot grid.")
    args = parser.parse_args(argv)

    config = build_2d_target_position_config()
    if args.pilot:
        _apply_pilot_mode(config)
    config_path = ROOT / "configs" / "transport_2d_target_position_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_2d_target_position" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    results_payload = _load_results()
    if not args.skip_visuals:
        chosen = selected_scenario_names(results_payload, top_n=2, bottom_n=1)
        command = [sys.executable, str(ROOT / "scripts" / "run_transport_visual_journey1.py"), "--config", str(config_path), "--results", str(results_path)]
        for name in chosen:
            command.extend(["--scenario-name", name])
        _run(command)
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_2d_target_position" / "latest" / "campaign_review"
    agg = _aggregate(results_payload)
    _plot_dashboard(results_payload, review_dir / "2d_target_ranking.png")
    _plot_heatmap(agg, review_dir / "2d_target_heatmaps.png")
    _write_summary(results_payload, review_dir)
    (review_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
