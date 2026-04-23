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


SEEDS_12 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
PILOT_SEEDS = [3, 5, 7, 11, 13, 17]
LITERATURE_GUARDRAILS = [
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Environment-assisted transport should be evaluated through target efficiency, not by coherence or spreading alone."},
    {"key": "Manzano2013", "url": "https://doi.org/10.1371/journal.pone.0057041", "reading": "Useful transfer to a sink is not identical to internal redistribution through the network."},
    {"key": "MuelkenBlumen2011", "url": "https://doi.org/10.1016/j.physrep.2011.01.002", "reading": "Different network families can support very different propagation behavior even when they have comparable size."},
]


def build_material_full_config() -> dict[str, object]:
    expectation = {
        "expected_transport_trend": "Families with alternate paths should resist damage better than bottlenecked families, but target arrival and spreading need not rank the same way.",
        "expected_role_of_disorder": "Stronger disorder should lower arrival and reveal whether a family is structurally robust or fragile.",
        "expected_role_of_phase_scrambling": "Moderate phase scrambling may help only in families where coherent geometry creates harmful path competition.",
        "expected_failure_mode": "A family that only spreads more but does not improve useful arrival should not be called better transport.",
    }
    scenarios = [
        {
            "name": "Material full molecular-wire-like chain",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 9,
            "trap_site": 0,
            "medium": {"medium_type": "chain_1d", "n_sites": 10, "length_scale": 1.0, "coupling_law": "nearest_neighbor", "site_energy_profile": "static_disorder", "sink_definition": {"mode": "single_site", "site_index": 0}, "loss_definition": {"mode": "uniform_local_loss"}, "interface_axis": "x", "interface_position": 4.5},
            "literature_expectation": expectation,
        },
        {
            "name": "Material full ring aggregate",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 5,
            "trap_site": 0,
            "medium": {"medium_type": "ring", "n_sites": 10, "length_scale": 1.0, "coupling_law": "nearest_neighbor", "site_energy_profile": "static_disorder", "sink_definition": {"mode": "single_site", "site_index": 0}, "loss_definition": {"mode": "uniform_local_loss"}, "interface_axis": "x", "interface_position": 0.0},
            "literature_expectation": expectation,
        },
        {
            "name": "Material full disordered 2D sheet",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 15,
            "trap_site": 0,
            "medium": {"medium_type": "square_lattice_2d", "n_rows": 4, "n_cols": 4, "length_scale": 1.0, "coupling_law": "nearest_neighbor", "site_energy_profile": "static_disorder", "sink_definition": {"mode": "single_site", "site_index": 0}, "loss_definition": {"mode": "uniform_local_loss"}, "interface_axis": "x", "interface_position": 1.5},
            "literature_expectation": expectation,
        },
        {
            "name": "Material full bottleneck medium",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 17,
            "trap_site": 0,
            "medium": {"medium_type": "bottleneck_lattice", "n_rows": 3, "n_cols_left": 3, "n_cols_right": 3, "length_scale": 1.0, "coupling_law": "nearest_neighbor", "site_energy_profile": "static_disorder", "sink_definition": {"mode": "single_site", "site_index": 0}, "loss_definition": {"mode": "uniform_local_loss"}, "interface_axis": "x", "interface_position": 3.0},
            "literature_expectation": expectation,
        },
        {
            "name": "Material full clustered medium",
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "initial_site": 11,
            "trap_site": 0,
            "medium": {"medium_type": "clustered_lattice", "cluster_size": 3, "length_scale": 1.0, "coupling_law": "nearest_neighbor", "site_energy_profile": "static_disorder", "sink_definition": {"mode": "single_site", "site_index": 0}, "loss_definition": {"mode": "uniform_local_loss"}, "interface_axis": "x", "interface_position": 3.0},
            "literature_expectation": expectation,
        },
    ]
    return {
        "study_name": "Material-inspired full campaign",
        "output_subdir": "medium_material_full",
        "time_grid": {"t_final": 18.0, "n_samples": 220},
        "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
        "sweep": {"disorder_strength_over_coupling": [0.0, 0.4, 0.8, 1.2], "dephasing_over_coupling": [0.0, 0.05, 0.2, 0.6, 1.0]},
        "ensemble_seeds": SEEDS_12,
        "scenarios": scenarios,
    }


def _apply_pilot_mode(config: dict[str, object]) -> None:
    config["runtime_mode"] = "interactive_pilot"
    config["pilot_note"] = "Reduced seeds and phase-scrambling grid for interactive review; use without --pilot for the 12-seed confirmatory run."
    config["ensemble_seeds"] = PILOT_SEEDS
    config["time_grid"] = {"t_final": 18.0, "n_samples": 160}
    sweep = dict(config["sweep"])
    sweep["dephasing_over_coupling"] = [0.0, 0.1, 0.4, 0.8]
    config["sweep"] = sweep


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results() -> dict[str, object]:
    return json.loads((ROOT / "outputs" / "transport_networks" / "medium_material_full" / "latest" / "results.json").read_text(encoding="utf-8"))


def _aggregate(results_payload: dict[str, object]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for scenario in results_payload["scenarios"]:
        derived = best_by_disorder(scenario)
        rows.append(
            {
                "scenario": str(scenario["scenario_name"]).replace("Material full ", ""),
                "arrival": float(np.mean(derived["best"])),
                "spreading": float(np.mean(np.asarray(scenario["spreading_mean"], dtype=float))),
                "mixing": float(np.mean(np.asarray(scenario["mixing_mean"], dtype=float))),
                "gain": float(np.mean(derived["gain"])),
            }
        )
    return rows


def _plot_dashboard(rows: list[dict[str, float | str]], output_path: Path) -> None:
    labels = [str(row["scenario"]) for row in rows]
    arrival = np.asarray([float(row["arrival"]) for row in rows], dtype=float)
    spreading = np.asarray([float(row["spreading"]) for row in rows], dtype=float)
    mixing = np.asarray([float(row["mixing"]) for row in rows], dtype=float)
    spreading_norm = spreading / max(float(np.max(spreading)), 1e-12)
    mixing_norm = mixing / max(float(np.max(mixing)), 1e-12)
    width = 0.24
    x = np.arange(len(rows))
    fig, axis = plt.subplots(figsize=(13.5, 6.0), constrained_layout=False)
    axis.bar(x - width, arrival, width=width, color="#2563eb", label="target arrival")
    axis.bar(x, spreading_norm, width=width, color="#16a34a", label="spreading normalized")
    axis.bar(x + width, mixing_norm, width=width, color="#f97316", label="mixing normalized")
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=25, ha="right")
    axis.set_ylabel("relative scale")
    axis.set_title("arrival, spreading, and mixing are different quantities")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0.0, 1.18))
    fig.suptitle("Material-inspired full campaign", fontsize=16, weight="bold", y=0.99)
    fig.subplots_adjust(top=0.78, bottom=0.28, left=0.08, right=0.98)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(results_payload: dict[str, object], output_path: Path) -> None:
    rows = _aggregate(results_payload)
    families = [str(row["scenario"]) for row in rows]
    disorders = np.asarray([0.0, 0.4, 0.8, 1.2], dtype=float)
    arrival_grid = np.zeros((len(families), len(disorders)), dtype=float)
    phase_grid = np.zeros((len(families), len(disorders)), dtype=float)
    for family_index, scenario in enumerate(results_payload["scenarios"]):
        derived = best_by_disorder(scenario)
        arrival_grid[family_index, :] = derived["best"]
        phase_grid[family_index, :] = derived["best_dephasing"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    im0 = axes[0].imshow(arrival_grid, origin="lower", aspect="auto", cmap="viridis")
    im1 = axes[1].imshow(phase_grid, origin="lower", aspect="auto", cmap="plasma")
    axes[0].set_title("best arrival")
    axes[1].set_title("best phase-scrambling")
    for axis in axes:
        axis.set_xticks(np.arange(len(disorders)))
        axis.set_xticklabels([f"{value:.1f}" for value in disorders])
        axis.set_yticks(np.arange(len(families)))
        axis.set_yticklabels(families)
        axis.set_xlabel("local irregularity / coherent coupling")
        axis.set_ylabel("family")
    fig.colorbar(im0, ax=axes[0], shrink=0.85, label="final target population")
    fig.colorbar(im1, ax=axes[1], shrink=0.85, label="best relative phase-scrambling rate")
    fig.suptitle("Material-inspired full heatmaps", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(rows: list[dict[str, float | str]], output_dir: Path) -> None:
    best_family = max(rows, key=lambda item: float(item["arrival"]))
    spread_only = [str(row["scenario"]) for row in rows if float(row["spreading"]) >= np.mean([float(item["spreading"]) for item in rows]) and float(row["arrival"]) < np.mean([float(item["arrival"]) for item in rows])]
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="Material-inspired full campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[f"Generated at UTC: {datetime.now(UTC).isoformat()}", "Goal: compare several effective material families without overselling them as microscopic materials models."],
        measured_lines=[f"Best family by useful arrival: {best_family['scenario']} with mean best arrival {float(best_family['arrival']):.3f}.", f"Families that spread relatively well without above-average useful arrival: {', '.join(spread_only) if spread_only else 'none'}."],
        agreement_lines=["This agrees with the literature if useful arrival and internal spreading are not treated as the same thing.", "A bottlenecked family should usually look worse than a family with alternate paths if the geometry matters."],
        uncertainty_lines=["These are effective media, not microscopic materials models with fitted couplings.", "The first pass uses nearest-neighbor coupling only; long-range structure has not yet been tested."],
        table_headers=["family", "mean best arrival", "mean spreading", "mean mixing", "mean gain"],
        table_rows=[[str(row["scenario"]), f"{float(row['arrival']):.3f}", f"{float(row['spreading']):.3f}", f"{float(row['mixing']):.3f}", f"{float(row['gain']):.3f}"] for row in rows],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full material-inspired campaign.")
    parser.add_argument("--skip-simulation", action="store_true")
    parser.add_argument("--skip-visuals", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Run the lighter interactive pilot grid.")
    args = parser.parse_args(argv)

    config = build_material_full_config()
    if args.pilot:
        _apply_pilot_mode(config)
    config_path = ROOT / "configs" / "transport_material_full_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_material_full" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    results_payload = _load_results()
    if not args.skip_visuals:
        chosen = selected_scenario_names(results_payload, top_n=2, bottom_n=1)
        command = [sys.executable, str(ROOT / "scripts" / "run_transport_visual_journey1.py"), "--config", str(config_path), "--results", str(results_path)]
        for name in chosen:
            command.extend(["--scenario-name", name])
        _run(command)
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_material_full" / "latest" / "campaign_review"
    rows = _aggregate(results_payload)
    _plot_dashboard(rows, review_dir / "material_full_dashboard.png")
    _plot_heatmap(results_payload, review_dir / "material_full_heatmaps.png")
    _write_summary(rows, review_dir)
    (review_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
