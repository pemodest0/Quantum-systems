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
LITERATURE_GUARDRAILS = [
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Moderate dephasing can improve transport when coherent motion gets trapped by interference or disorder."},
    {"key": "PlenioHuelga2008", "url": "https://doi.org/10.1088/1367-2630/10/11/113019", "reading": "There is typically an assistance window at weak or moderate noise, followed by suppression at stronger noise."},
    {"key": "Rebentrost2009", "url": "https://doi.org/10.1088/1367-2630/11/3/033003", "reading": "A sink-efficiency scan over disorder and dephasing is the standard diagnosis for environment-assisted transport."},
    {"key": "Maier2019", "url": "https://doi.org/10.1103/PhysRevLett.122.050501", "reading": "Experiments support a progression from coherent motion to assistance and then suppression at stronger noise."},
]


def build_ring_ceiling_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "The favorable target should remain mostly coherent-optimal, while the unfavorable target may show a dephasing-assisted window.",
        "expected_role_of_disorder": "Medium and high disorder should lower target arrival and make the ring more sensitive to the environment.",
        "expected_role_of_phase_scrambling": "Weak or moderate phase scrambling can help the unfavorable target, but strong values should eventually suppress arrival.",
        "expected_failure_mode": "If the scan reaches high enough phase scrambling, the assisted curve should bend down again.",
    }
    return {
        "study_name": "Ring ceiling campaign",
        "output_subdir": "medium_ring_ceiling",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {
            "disorder_strength_over_coupling": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4],
            "dephasing_over_coupling": [0.0, 0.02, 0.05, 0.08, 0.12, 0.16, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6],
        },
        "ensemble_seeds": SEEDS_16,
        "scenarios": [
            {
                "name": "Ring ceiling favorable target",
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
                "name": "Ring ceiling unfavorable target",
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
                "literature_expectation": expectation,
            },
        ],
    }


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results(output_subdir: str) -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / output_subdir / "latest" / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _ceiling_reached(payload: dict[str, object]) -> bool:
    efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
    dephasing = np.asarray(payload["dephasing_over_coupling"], dtype=float)
    last_col = efficiency[:, -1]
    for disorder_index in range(efficiency.shape[0]):
        best_col = int(np.nanargmax(efficiency[disorder_index]))
        if 0 < best_col < efficiency.shape[1] - 1:
            best_value = float(efficiency[disorder_index, best_col])
            tail_value = float(last_col[disorder_index])
            if dephasing[best_col] >= 0.2 and best_value - tail_value >= 0.03:
                return True
    return False


def _plot_dashboard(results_payload: dict[str, object], output_path: Path) -> None:
    scenarios = list(results_payload["scenarios"])
    colors = ["#2563eb", "#dc2626"]
    labels = ["favorable target", "unfavorable target"]
    derived = [best_by_disorder(item) for item in scenarios]
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
    fig.suptitle("Ring ceiling campaign", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmaps(results_payload: dict[str, object], output_path: Path) -> None:
    scenarios = list(results_payload["scenarios"])
    fig, axes = plt.subplots(2, len(scenarios), figsize=(6.2 * len(scenarios), 8.2), constrained_layout=True)
    for col, payload in enumerate(scenarios):
        disorder = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
        dephasing = np.asarray(payload["dephasing_over_coupling"], dtype=float)
        efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
        confidence = np.asarray(payload["regime_confidence_grid"], dtype=float)
        im0 = axes[0, col].imshow(efficiency, origin="lower", aspect="auto", cmap="viridis")
        im1 = axes[1, col].imshow(confidence, origin="lower", aspect="auto", cmap="magma", vmin=0.0, vmax=1.0)
        axes[0, col].set_title(f"{payload['scenario_name']}: arrival")
        axes[1, col].set_title(f"{payload['scenario_name']}: regime confidence")
        for axis in axes[:, col]:
            axis.set_xticks(np.arange(len(dephasing)))
            axis.set_xticklabels([f"{value:.2f}" for value in dephasing], rotation=45, ha="right")
            axis.set_yticks(np.arange(len(disorder)))
            axis.set_yticklabels([f"{value:.1f}" for value in disorder])
            axis.set_xlabel("phase scrambling / coherent coupling")
            axis.set_ylabel("local irregularity / coherent coupling")
        fig.colorbar(im0, ax=axes[0, col], shrink=0.85, label="final target population")
        fig.colorbar(im1, ax=axes[1, col], shrink=0.85, label="classification confidence")
    fig.suptitle("Ring ceiling heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(results_payload: dict[str, object], output_dir: Path) -> None:
    scenarios = list(results_payload["scenarios"])
    unfavorable = next(item for item in scenarios if "unfavorable" in str(item["scenario_name"]).lower())
    favorable = next(
        item
        for item in scenarios
        if "favorable" in str(item["scenario_name"]).lower()
        and "unfavorable" not in str(item["scenario_name"]).lower()
    )
    fav = best_by_disorder(favorable)
    unfav = best_by_disorder(unfavorable)
    ceiling = _ceiling_reached(unfavorable)
    table_headers = ["scenario", "disorder", "zero scrambling", "best arrival", "gain", "best phase scrambling", "spread"]
    table_rows: list[list[str]] = []
    for label, derived in [("favorable target", fav), ("unfavorable target", unfav)]:
        for index, disorder_value in enumerate(derived["disorder"]):
            table_rows.append(
                [
                    label,
                    f"{float(disorder_value):.2f}",
                    f"{float(derived['coherent'][index]):.3f}",
                    f"{float(derived['best'][index]):.3f}",
                    f"{float(derived['gain'][index]):.3f}",
                    f"{float(derived['best_dephasing'][index]):.2f}",
                    f"{float(derived['best_std'][index]):.3f}",
                ]
            )
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="Ring ceiling campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[
            f"Generated at UTC: {datetime.now(UTC).isoformat()}",
            "Goal: test whether the unfavorable target eventually turns down at stronger phase scrambling.",
        ],
        measured_lines=[
            f"Favorable target mean gain over the scan stayed small: max gain = {float(np.max(fav['gain'])):.3f}.",
            f"Unfavorable target showed a much larger gain: max gain = {float(np.max(unfav['gain'])):.3f}.",
            f"Unfavorable target best phase-scrambling values stayed in the moderate range, with maximum {float(np.max(unfav['best_dephasing'])):.2f}.",
        ],
        agreement_lines=[
            "This agrees with the literature if the unfavorable target improves under moderate phase scrambling while the favorable target stays near the coherent optimum.",
            f"Ceiling reached status: {'yes' if ceiling else 'no'}.",
        ],
        uncertainty_lines=[
            "If the unfavorable-target curve has not bent down by the end of the scan, the full assistance window is still not proven.",
            "This campaign uses 16 seeds, so it is suitable for interactive review but not yet the final confirmatory run.",
        ],
        table_headers=table_headers,
        table_rows=table_rows,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ring ceiling campaign.")
    parser.add_argument("--skip-simulation", action="store_true", help="Reuse existing results and rebuild dashboards only.")
    parser.add_argument("--skip-visuals", action="store_true", help="Do not regenerate Journey 1 GIFs and 3D surfaces.")
    args = parser.parse_args(argv)

    config = build_ring_ceiling_config()
    config_path = ROOT / "configs" / "transport_ring_ceiling_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_ring_ceiling" / "latest" / "results.json"
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
                "Ring ceiling favorable target",
                "--scenario-name",
                "Ring ceiling unfavorable target",
            ]
        )
    results_payload = _load_results("medium_ring_ceiling")
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_ring_ceiling" / "latest" / "campaign_review"
    _plot_dashboard(results_payload, review_dir / "ring_ceiling_dashboard.png")
    _plot_heatmaps(results_payload, review_dir / "ring_ceiling_heatmaps.png")
    _write_summary(results_payload, review_dir)
    (review_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "config": str(config_path),
                "results": str(results_path),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
