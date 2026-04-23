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
LITERATURE_GUARDRAILS = [
    {"key": "Razzoli2021", "url": "https://doi.org/10.3390/e23010085", "reading": "Trap position changes transport efficiency on graphs and must be treated as a core variable."},
    {"key": "Rebentrost2009", "url": "https://doi.org/10.1088/1367-2630/11/3/033003", "reading": "Environment-assisted transport should be diagnosed by comparing sink efficiency with and without dephasing."},
    {"key": "PlenioHuelga2008", "url": "https://doi.org/10.1088/1367-2630/10/11/113019", "reading": "The environment should matter differently when the coherent baseline is favorable versus frustrated."},
]


def build_ring_target_sweep_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "Different targets on the same ring should not be treated as equivalent, because the target changes the coherent pathways.",
        "expected_role_of_disorder": "Higher irregularity should lower the absolute arrival, but may also make weak phase scrambling more useful for unfavorable targets.",
        "expected_role_of_phase_scrambling": "Targets that are coherent-friendly should stay close to the zero-scrambling optimum; unfavorable targets may need a nonzero optimum.",
        "expected_failure_mode": "If all targets collapse to the same behavior, target placement is not acting as a first-order variable in this setup.",
    }
    scenarios: list[dict[str, object]] = []
    for trap_site in [0, 1, 2, 3]:
        scenarios.append(
            {
                "name": f"Ring target sweep trap {trap_site}",
                "coupling_hz": 1.0,
                "sink_rate_hz": 0.65,
                "loss_rate_hz": 0.02,
                "initial_site": 4,
                "trap_site": trap_site,
                "medium": {
                    "medium_type": "ring",
                    "n_sites": 8,
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
        "study_name": "Ring target sweep campaign",
        "output_subdir": "medium_ring_target_sweep",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.6, 0.8, 1.0, 1.2],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
        },
        "ensemble_seeds": SEEDS_16,
        "scenarios": scenarios,
    }


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "medium_ring_target_sweep" / "latest" / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _trap_from_name(name: str) -> int:
    return int(name.split()[-1])


def _aggregate(results_payload: dict[str, object]) -> dict[str, np.ndarray]:
    disorders = [0.6, 0.8, 1.0, 1.2]
    traps = [0, 1, 2, 3]
    best_arrival = np.zeros((len(traps), len(disorders)), dtype=float)
    best_phase = np.zeros((len(traps), len(disorders)), dtype=float)
    ranking_mean = np.zeros(len(traps), dtype=float)
    for scenario in results_payload["scenarios"]:
        trap = _trap_from_name(str(scenario["scenario_name"]))
        derived = best_by_disorder(scenario)
        best_arrival[traps.index(trap), :] = derived["best"]
        best_phase[traps.index(trap), :] = derived["best_dephasing"]
        ranking_mean[traps.index(trap)] = float(np.mean(derived["best"]))
    return {
        "disorders": np.asarray(disorders, dtype=float),
        "traps": np.asarray(traps, dtype=int),
        "best_arrival": best_arrival,
        "best_phase": best_phase,
        "ranking_mean": ranking_mean,
    }


def _plot_dashboard(results_payload: dict[str, object], output_path: Path) -> None:
    agg = _aggregate(results_payload)
    order = np.argsort(agg["ranking_mean"])[::-1]
    labels = [f"trap {int(agg['traps'][idx])}" for idx in order]
    values = agg["ranking_mean"][order]
    fig, axis = plt.subplots(figsize=(10.0, 4.8), constrained_layout=True)
    axis.bar(labels, values, color="#2563eb")
    axis.set_ylabel("mean best arrival across disorder scan")
    axis.set_title("target ranking by useful arrival")
    axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Ring target sweep ranking", fontsize=16, weight="bold")
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
    fig.suptitle("Ring target sweep heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(results_payload: dict[str, object], output_dir: Path) -> None:
    agg = _aggregate(results_payload)
    ranking_order = np.argsort(agg["ranking_mean"])[::-1]
    top_trap = int(agg["traps"][ranking_order[0]])
    bottom_trap = int(agg["traps"][ranking_order[-1]])
    table_headers = ["target index", "disorder", "best arrival", "best phase scrambling"]
    table_rows: list[list[str]] = []
    for trap_index, trap in enumerate(agg["traps"]):
        for disorder_index, disorder_value in enumerate(agg["disorders"]):
            table_rows.append(
                [
                    str(int(trap)),
                    f"{float(disorder_value):.2f}",
                    f"{float(agg['best_arrival'][trap_index, disorder_index]):.3f}",
                    f"{float(agg['best_phase'][trap_index, disorder_index]):.3f}",
                ]
            )
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="Ring target sweep campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[
            f"Generated at UTC: {datetime.now(UTC).isoformat()}",
            "Goal: map how target placement changes useful arrival and the best environment strength on the same ring.",
        ],
        measured_lines=[
            f"Best-ranked target: trap {top_trap}. Worst-ranked target: trap {bottom_trap}.",
            f"Ranking gap between best and worst targets: {float(agg['ranking_mean'][ranking_order[0]] - agg['ranking_mean'][ranking_order[-1]]):.3f}.",
        ],
        agreement_lines=[
            "This agrees with the literature if the ranking is not flat and the best phase-scrambling values depend on the target.",
            "If the same target remains best across disorder values, target placement is acting as a first-order variable here.",
        ],
        uncertainty_lines=[
            "A ranking based on the mean over disorder compresses the details of each disorder row into one number per target.",
            "The present interactive run uses 16 seeds; a paper-grade confirmation would still need a heavier repeat.",
        ],
        table_headers=table_headers,
        table_rows=table_rows,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ring target sweep campaign.")
    parser.add_argument("--skip-simulation", action="store_true", help="Reuse existing results and rebuild dashboards only.")
    parser.add_argument("--skip-visuals", action="store_true", help="Do not regenerate selected Journey 1 visuals.")
    args = parser.parse_args(argv)

    config = build_ring_target_sweep_config()
    config_path = ROOT / "configs" / "transport_ring_target_sweep_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_ring_target_sweep" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    results_payload = _load_results()
    if not args.skip_visuals:
        chosen = selected_scenario_names(results_payload, top_n=2, bottom_n=1)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_transport_visual_journey1.py"),
            "--config",
            str(config_path),
            "--results",
            str(results_path),
        ]
        for scenario_name in chosen:
            command.extend(["--scenario-name", scenario_name])
        _run(command)
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_ring_target_sweep" / "latest" / "campaign_review"
    agg = _aggregate(results_payload)
    _plot_dashboard(results_payload, review_dir / "ring_target_ranking.png")
    _plot_heatmap(agg, review_dir / "ring_target_heatmaps.png")
    _write_summary(results_payload, review_dir)
    (review_dir / "run_metadata.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
