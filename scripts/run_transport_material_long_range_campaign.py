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

from oqs_transport import average_best_arrival, best_by_disorder, selected_scenario_names, write_literature_guardrails, write_summary_markdown  # noqa: E402


SEEDS_12 = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
PILOT_SEEDS = [3, 5, 7, 11, 13, 17]
LITERATURE_GUARDRAILS = [
    {"key": "MuelkenBlumen2011", "url": "https://doi.org/10.1016/j.physrep.2011.01.002", "reading": "Changing the network couplings can qualitatively change transport pathways."},
    {"key": "Mohseni2008", "url": "https://doi.org/10.1063/1.3002335", "reading": "Transport claims should be judged by useful arrival, not by added complexity alone."},
]


def _load_material_full_results() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "medium_material_full" / "latest" / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_material_full_config() -> dict[str, object]:
    path = ROOT / "outputs" / "transport_networks" / "medium_material_full" / "latest" / "config_used.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_winners(results_payload: dict[str, object]) -> list[dict[str, object]]:
    ranking = sorted(list(results_payload["scenarios"]), key=average_best_arrival, reverse=True)
    return ranking[:2]


def _long_range_medium(base_medium: dict[str, object]) -> dict[str, object]:
    medium = dict(base_medium)
    medium["coupling_law"] = "exponential_decay"
    medium["decay_length"] = 1.5
    medium["cutoff_radius"] = 2.6
    return medium


def _clean_medium(raw_medium: dict[str, object]) -> dict[str, object]:
    return {str(key): value for key, value in raw_medium.items() if value is not None}


def build_material_long_range_config(base_results: dict[str, object], base_config: dict[str, object]) -> dict[str, object]:
    winners = _pick_winners(base_results)
    config_by_name = {str(scenario["name"]): scenario for scenario in base_config["scenarios"]}
    expectation = {
        "expected_transport_trend": "Long-range coupling should only be kept if it changes useful arrival in a material way.",
        "expected_role_of_disorder": "Disorder can either blunt or amplify the effect of a longer coupling range.",
        "expected_role_of_phase_scrambling": "If long-range coupling already bypasses bottlenecks, the environment may matter less.",
        "expected_failure_mode": "If the long-range variant does not improve useful arrival, the added complexity is not earned.",
    }
    scenarios: list[dict[str, object]] = []
    for scenario in winners:
        base_name = str(scenario["scenario_name"]).replace("Material full ", "")
        config_scenario = config_by_name[str(scenario["scenario_name"])]
        medium = _clean_medium(dict(config_scenario["medium"]))
        scenarios.append(
            {
                "name": f"Material baseline {base_name}",
                "coupling_hz": float(config_scenario["coupling_hz"]),
                "sink_rate_hz": float(config_scenario["sink_rate_hz"]),
                "loss_rate_hz": float(config_scenario["loss_rate_hz"]),
                "initial_site": int(config_scenario["initial_site"]),
                "trap_site": int(config_scenario["trap_site"]),
                "medium": medium,
                "literature_expectation": expectation,
            }
        )
        scenarios.append(
            {
                "name": f"Material long-range {base_name}",
                "coupling_hz": float(config_scenario["coupling_hz"]),
                "sink_rate_hz": float(config_scenario["sink_rate_hz"]),
                "loss_rate_hz": float(config_scenario["loss_rate_hz"]),
                "initial_site": int(config_scenario["initial_site"]),
                "trap_site": int(config_scenario["trap_site"]),
                "medium": _long_range_medium(medium),
                "literature_expectation": expectation,
            }
        )
    return {
        "study_name": "Material long-range winner campaign",
        "output_subdir": "medium_material_long_range",
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
    return json.loads((ROOT / "outputs" / "transport_networks" / "medium_material_long_range" / "latest" / "results.json").read_text(encoding="utf-8"))


def _aggregate(results_payload: dict[str, object]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for scenario in results_payload["scenarios"]:
        derived = best_by_disorder(scenario)
        rows.append(
            {
                "scenario": str(scenario["scenario_name"]).replace("Material ", ""),
                "arrival": float(np.mean(derived["best"])),
                "gain": float(np.mean(derived["gain"])),
                "phase": float(np.mean(derived["best_dephasing"])),
            }
        )
    return rows


def _plot_dashboard(rows: list[dict[str, float | str]], output_path: Path) -> None:
    labels = [str(row["scenario"]) for row in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8), constrained_layout=True)
    axes[0].bar(x, [float(row["arrival"]) for row in rows], color="#2563eb")
    axes[0].set_title("mean best arrival")
    axes[1].bar(x, [float(row["gain"]) for row in rows], color="#16a34a")
    axes[1].set_title("mean gain")
    axes[2].bar(x, [float(row["phase"]) for row in rows], color="#f97316")
    axes[2].set_title("mean best phase-scrambling")
    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=25, ha="right")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Long-range variants for winning material families", fontsize=16, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(rows: list[dict[str, float | str]], output_path: Path) -> None:
    labels = [str(row["scenario"]) for row in rows]
    data = np.array(
        [
            [float(row["arrival"]) for row in rows],
            [float(row["gain"]) for row in rows],
            [float(row["phase"]) for row in rows],
        ],
        dtype=float,
    )
    fig, axis = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    image = axis.imshow(data, origin="lower", aspect="auto", cmap="viridis")
    axis.set_xticks(np.arange(len(labels)))
    axis.set_xticklabels(labels, rotation=25, ha="right")
    axis.set_yticks([0, 1, 2])
    axis.set_yticklabels(["mean best arrival", "mean gain", "mean best phase"])
    fig.colorbar(image, ax=axis, shrink=0.85, label="relative value")
    fig.suptitle("Long-range winner comparison heatmap", fontsize=16, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(rows: list[dict[str, float | str]], output_dir: Path) -> None:
    deltas: list[str] = []
    by_family: dict[str, dict[str, float]] = {}
    for row in rows:
        name = str(row["scenario"])
        variant, family = name.split(" ", 1)
        by_family.setdefault(family, {})[variant] = float(row["arrival"])
    for family, mapping in by_family.items():
        if "baseline" in mapping and "long-range" in mapping:
            deltas.append(f"{family}: delta arrival = {mapping['long-range'] - mapping['baseline']:+.3f}")
    write_literature_guardrails(output_dir / "literature_guardrails.json", LITERATURE_GUARDRAILS)
    write_summary_markdown(
        output_dir / "summary.md",
        title="Material long-range winner campaign",
        literature_guardrails=LITERATURE_GUARDRAILS,
        overview_lines=[f"Generated at UTC: {datetime.now(UTC).isoformat()}", "Goal: give long-range coupling a fair test only on the two best families from the full material campaign."],
        measured_lines=deltas or ["No baseline/long-range pairs were formed."],
        agreement_lines=["This agrees with the literature only if the long-range variant changes useful arrival, not just complexity on paper.", "If the delta is below about 0.03 in arrival, the added coupling range has not clearly earned its keep."],
        uncertainty_lines=["This comparison uses the same disorder/dephasing grid as the nearest-neighbor campaign and is meant as a controlled follow-up, not a full redesign.", "If a family changes only its gain or best phase by a tiny amount, the conclusion should remain 'no material change.'"],
        table_headers=["scenario", "mean best arrival", "mean gain", "mean best phase"],
        table_rows=[[str(row["scenario"]), f"{float(row['arrival']):.3f}", f"{float(row['gain']):.3f}", f"{float(row['phase']):.3f}"] for row in rows],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the long-range winner campaign for material-inspired families.")
    parser.add_argument("--skip-simulation", action="store_true")
    parser.add_argument("--skip-visuals", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Run the lighter interactive pilot grid.")
    args = parser.parse_args(argv)

    base_results = _load_material_full_results()
    base_config = _load_material_full_config()
    config = build_material_long_range_config(base_results, base_config)
    if args.pilot:
        _apply_pilot_mode(config)
    config_path = ROOT / "configs" / "transport_material_long_range_campaign.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    results_path = ROOT / "outputs" / "transport_networks" / "medium_material_long_range" / "latest" / "results.json"
    if not args.skip_simulation or not results_path.exists():
        _run([sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)])
    results_payload = _load_results()
    if not args.skip_visuals:
        chosen = selected_scenario_names(results_payload, top_n=2, bottom_n=0)
        command = [sys.executable, str(ROOT / "scripts" / "run_transport_visual_journey1.py"), "--config", str(config_path), "--results", str(results_path)]
        for name in chosen:
            command.extend(["--scenario-name", name])
        _run(command)
    review_dir = ROOT / "outputs" / "transport_networks" / "medium_material_long_range" / "latest" / "campaign_review"
    rows = _aggregate(results_payload)
    _plot_dashboard(rows, review_dir / "material_long_range_dashboard.png")
    _plot_heatmap(rows, review_dir / "material_long_range_heatmap.png")
    _write_summary(rows, review_dir)
    (review_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "config": str(config_path), "results": str(results_path)}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
