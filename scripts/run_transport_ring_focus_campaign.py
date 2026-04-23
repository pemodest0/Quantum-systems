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

SEEDS_32 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137]

LITERATURE_GUARDRAILS = [
    {
        "key": "Mohseni2008",
        "url": "https://doi.org/10.1063/1.3002335",
        "reading": "Moderate phase scrambling can improve transport when coherent motion is trapped by interference or disorder.",
    },
    {
        "key": "PlenioHuelga2008",
        "url": "https://doi.org/10.1088/1367-2630/10/11/113019",
        "reading": "Noise can help dissipative-network transport, but excessive noise suppresses useful coherent propagation.",
    },
    {
        "key": "Rebentrost2009",
        "url": "https://doi.org/10.1088/1367-2630/11/3/033003",
        "reading": "Target efficiency under a dephasing scan is a standard way to diagnose environment-assisted transport.",
    },
    {
        "key": "Manzano2013",
        "url": "https://doi.org/10.1371/journal.pone.0057041",
        "reading": "Excitation transfer to a sink and energy transfer need not behave the same; here we track target population only.",
    },
    {
        "key": "Novo2016",
        "url": "https://doi.org/10.1038/srep18142",
        "reading": "Disorder and dephasing must be scanned together; ensemble averaging is required before robustness claims.",
    },
    {
        "key": "Razzoli2021",
        "url": "https://doi.org/10.3390/e23010085",
        "reading": "Transport efficiency depends on graph structure, starting site, and trap site; target placement is not a detail.",
    },
    {
        "key": "Maier2019",
        "url": "https://doi.org/10.1103/PhysRevLett.122.050501",
        "reading": "Experiments observe crossover from coherent dynamics and localization to noise-assisted transport and then suppression at strong noise.",
    },
]


def _campaign_config() -> dict[str, object]:
    expectation_common = {
        "expected_transport_trend": "A symmetric target should preserve stronger coherent arrival, while an off-symmetry target can need moderate phase scrambling.",
        "expected_role_of_disorder": "Medium and high local irregularity should reduce arrival and expose whether weak scrambling can recover transport.",
        "expected_role_of_phase_scrambling": "Weak or moderate phase scrambling can help if coherent interference blocks the target, but large scrambling should suppress motion.",
        "expected_failure_mode": "Strong irregularity plus strong scrambling should reduce both useful arrival and coherent spreading.",
    }
    return {
        "study_name": "Ring focused R1-R3 campaign",
        "output_subdir": "medium_ring_focus_r1_r3",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2],
            "dephasing_over_coupling": [0.0, 0.02, 0.05, 0.08, 0.12, 0.16, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0],
        },
        "ensemble_seeds": SEEDS_32,
        "scenarios": [
            {
                "name": "Ring favorable target",
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
                "literature_expectation": expectation_common,
            },
            {
                "name": "Ring unfavorable target",
                "coupling_hz": 1.0,
                "sink_rate_hz": 0.65,
                "loss_rate_hz": 0.02,
                "initial_site": 4,
                "trap_site": 1,
                "medium": {
                    "medium_type": "ring",
                    "n_sites": 8,
                    "length_scale": 1.0,
                    "coupling_law": "nearest_neighbor",
                    "site_energy_profile": "static_disorder",
                    "sink_definition": {"mode": "single_site", "site_index": 1},
                    "loss_definition": {"mode": "uniform_local_loss"},
                    "interface_axis": "x",
                    "interface_position": 0.0,
                },
                "literature_expectation": expectation_common,
            },
        ],
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "medium_ring_focus_r1_r3" / "latest" / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _best_by_disorder(payload: dict[str, object]) -> dict[str, np.ndarray]:
    efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
    efficiency_std = np.asarray(payload["efficiency_std"], dtype=float)
    disorder = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
    dephasing = np.asarray(payload["dephasing_over_coupling"], dtype=float)
    best_cols = np.nanargmax(efficiency, axis=1)
    coherent = efficiency[:, 0]
    best = efficiency[np.arange(len(disorder)), best_cols]
    best_std = efficiency_std[np.arange(len(disorder)), best_cols]
    best_dephasing = dephasing[best_cols]
    return {
        "disorder": disorder,
        "coherent": coherent,
        "best": best,
        "best_std": best_std,
        "best_dephasing": best_dephasing,
        "gain": best - coherent,
    }


def _plot_focus_dashboard(results_payload: dict[str, object], output_path: Path) -> None:
    scenarios = list(results_payload["scenarios"])
    colors = ["#2563eb", "#dc2626"]
    labels = [str(item["scenario_name"]).replace("Ring ", "") for item in scenarios]
    derived = [_best_by_disorder(item) for item in scenarios]

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.0), constrained_layout=True)
    for item, color, label in zip(derived, colors, labels, strict=True):
        x = item["disorder"]
        axes[0, 0].plot(x, item["coherent"], color=color, ls="--", lw=1.8, alpha=0.70, label=f"{label}: zero scrambling")
        axes[0, 0].errorbar(x, item["best"], yerr=item["best_std"], color=color, lw=2.4, marker="o", capsize=4, label=f"{label}: best")
        axes[0, 1].plot(x, item["gain"], color=color, lw=2.4, marker="o", label=label)
        axes[1, 0].plot(x, item["best_dephasing"], color=color, lw=2.4, marker="o", label=label)
        axes[1, 1].plot(x, item["best_std"], color=color, lw=2.4, marker="o", label=label)

    axes[0, 0].set_title("arrival at the target")
    axes[0, 0].set_ylabel("final target population")
    axes[0, 1].set_title("gain from allowing phase scrambling")
    axes[0, 1].set_ylabel("best arrival minus zero-scrambling arrival")
    axes[1, 0].set_title("best phase-scrambling strength")
    axes[1, 0].set_ylabel("relative rate")
    axes[1, 1].set_title("ensemble spread at the best point")
    axes[1, 1].set_ylabel("standard deviation across disorder seeds")
    for axis in axes.ravel():
        axis.set_xlabel("local irregularity / coherent coupling")
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    fig.suptitle("Ring focus: favorable target versus unfavorable target", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_focus_heatmaps(results_payload: dict[str, object], output_path: Path) -> None:
    scenarios = list(results_payload["scenarios"])
    fig, axes = plt.subplots(2, len(scenarios), figsize=(6.0 * len(scenarios), 8.2), constrained_layout=True)
    if len(scenarios) == 1:
        axes = np.asarray(axes).reshape(2, 1)
    for col, payload in enumerate(scenarios):
        disorder = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
        dephasing = np.asarray(payload["dephasing_over_coupling"], dtype=float)
        efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
        confidence = np.asarray(payload["regime_confidence_grid"], dtype=float)
        im0 = axes[0, col].imshow(efficiency, origin="lower", aspect="auto", cmap="viridis")
        axes[0, col].set_title(f"{payload['scenario_name']}: arrival")
        im1 = axes[1, col].imshow(confidence, origin="lower", aspect="auto", cmap="magma", vmin=0.0, vmax=1.0)
        axes[1, col].set_title(f"{payload['scenario_name']}: regime confidence")
        for row_axis in axes[:, col]:
            row_axis.set_xticks(np.arange(len(dephasing)))
            row_axis.set_xticklabels([f"{value:.2f}" for value in dephasing], rotation=45, ha="right")
            row_axis.set_yticks(np.arange(len(disorder)))
            row_axis.set_yticklabels([f"{value:.1f}" for value in disorder])
            row_axis.set_xlabel("phase scrambling / coherent coupling")
            row_axis.set_ylabel("local irregularity / coherent coupling")
        fig.colorbar(im0, ax=axes[0, col], shrink=0.85, label="final target population")
        fig.colorbar(im1, ax=axes[1, col], shrink=0.85, label="classification confidence")
    fig.suptitle("Ring focus heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(results_payload: dict[str, object], output_path: Path) -> None:
    lines = [
        "# Ring focused R1/R3 campaign",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        "",
        "## Literature guardrails",
        "",
    ]
    for item in LITERATURE_GUARDRAILS:
        lines.append(f"- {item['key']}: {item['url']} -- {item['reading']}")
    lines.extend(
        [
            "",
            "## Derived rows",
            "",
            "| scenario | irregularity | zero scrambling arrival | best arrival | gain | best phase scrambling | ensemble spread |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    summary_payload: dict[str, object] = {"literature_guardrails": LITERATURE_GUARDRAILS, "rows": []}
    for scenario in results_payload["scenarios"]:
        derived = _best_by_disorder(scenario)
        for index, disorder_value in enumerate(derived["disorder"]):
            row = {
                "scenario": scenario["scenario_name"],
                "disorder": float(disorder_value),
                "zero_scrambling_arrival": float(derived["coherent"][index]),
                "best_arrival": float(derived["best"][index]),
                "gain": float(derived["gain"][index]),
                "best_phase_scrambling": float(derived["best_dephasing"][index]),
                "ensemble_spread": float(derived["best_std"][index]),
            }
            summary_payload["rows"].append(row)
            lines.append(
                f"| {row['scenario']} | {row['disorder']:.2f} | {row['zero_scrambling_arrival']:.3f} | "
                f"{row['best_arrival']:.3f} | {row['gain']:.3f} | {row['best_phase_scrambling']:.2f} | {row['ensemble_spread']:.3f} |"
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_json(output_path.with_suffix(".json"), summary_payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a focused ring campaign for R1/R3 refinement.")
    parser.add_argument("--skip-simulation", action="store_true", help="Reuse existing ring-focus results and regenerate only dashboards/visuals.")
    parser.add_argument("--skip-visuals", action="store_true", help="Do not regenerate best-vs-worst animations and 3D surfaces.")
    args = parser.parse_args(argv)

    config_path = ROOT / "configs" / "transport_ring_focus_campaign.json"
    _write_json(config_path, _campaign_config())

    results_path = ROOT / "outputs" / "transport_networks" / "medium_ring_focus_r1_r3" / "latest" / "results.json"
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
            ]
        )

    results_payload = _load_results()
    output_dir = ROOT / "outputs" / "transport_networks" / "medium_ring_focus_r1_r3" / "latest" / "focus_review"
    _plot_focus_dashboard(results_payload, output_dir / "ring_focus_dashboard.png")
    _plot_focus_heatmaps(results_payload, output_dir / "ring_focus_heatmaps.png")
    _write_summary(results_payload, output_dir / "ring_focus_summary.md")
    _write_json(
        output_dir / "run_metadata.json",
        {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "config": str(config_path),
            "results": str(results_path),
            "output_dir": str(output_dir),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
