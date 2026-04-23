from __future__ import annotations

import json
import subprocess
import sys
import argparse
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


SEEDS_8 = [3, 5, 7, 11, 13, 17, 19, 23]
SEEDS_12 = SEEDS_8 + [29, 31, 37, 41]
SEEDS_32 = SEEDS_12 + [43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137]


LITERATURE_CHECK = [
    {
        "key": "Mohseni2008",
        "url": "https://doi.org/10.1063/1.3002335",
        "use": "Environment-assisted transport benchmark: moderate dephasing can improve arrival when coherent motion is trapped by interference or disorder.",
    },
    {
        "key": "PlenioHuelga2008",
        "url": "https://doi.org/10.1088/1367-2630/10/11/113019",
        "use": "Noise can assist transport in network-like systems, but excessive dephasing suppresses useful coherent motion.",
    },
    {
        "key": "Rebentrost2009",
        "url": "https://doi.org/10.1088/1367-2630/11/3/033003",
        "use": "Sink efficiency and dephasing scans are standard metrics for excitation transport in open networks.",
    },
    {
        "key": "Caruso2009",
        "url": "https://doi.org/10.1063/1.3223548",
        "use": "Interplay of coherence, disorder, and trapping motivates tracking target population, coherence, and dissipative loss separately.",
    },
    {
        "key": "Manzano2013",
        "url": "https://doi.org/10.1371/journal.pone.0057041",
        "use": "Steady-state network transport separates excitation transfer from energy transfer and emphasizes sink-mediated efficiency.",
    },
    {
        "key": "Novo2016",
        "url": "https://doi.org/10.1038/srep18142",
        "use": "Disorder can sometimes assist transport outside the optimal decoherence regime, so robustness must be checked by ensembles.",
    },
    {
        "key": "MuelkenBlumen2011",
        "url": "https://doi.org/10.1016/j.physrep.2011.01.002",
        "use": "Continuous-time quantum walks on networks motivate topology-dependent transport comparisons.",
    },
    {
        "key": "Razzoli2021",
        "url": "https://doi.org/10.3390/e23010085",
        "use": "Graph-dependent transport efficiency depends on initial state, target placement, and propagation direction.",
    },
    {
        "key": "Coutinho2022",
        "url": "https://doi.org/10.1038/s42005-022-00866-7",
        "use": "Robustness should be treated as a network-level observable, not just a single best-case number.",
    },
]


def _expectation(
    transport: str,
    disorder: str,
    phase: str,
    failure: str,
) -> dict[str, str]:
    return {
        "expected_transport_trend": transport,
        "expected_role_of_disorder": disorder,
        "expected_role_of_phase_scrambling": phase,
        "expected_failure_mode": failure,
    }


def _medium(
    medium_type: str,
    *,
    n_sites: int | None = None,
    n_rows: int | None = None,
    n_cols: int | None = None,
    n_cols_left: int | None = None,
    n_cols_right: int | None = None,
    cluster_size: int | None = None,
    coupling_law: str = "nearest_neighbor",
    site_energy_profile: str = "static_disorder",
    length_scale: float = 1.0,
    decay_length: float = 1.5,
    power_law_exponent: float = 3.0,
    cutoff_radius: float | None = None,
    interface_axis: str | None = "x",
    interface_position: float | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "medium_type": medium_type,
        "length_scale": length_scale,
        "coupling_law": coupling_law,
        "site_energy_profile": site_energy_profile,
        "sink_definition": {"mode": "single_site"},
        "loss_definition": {"mode": "uniform_local_loss"},
        "decay_length": decay_length,
        "power_law_exponent": power_law_exponent,
    }
    for key, value in {
        "n_sites": n_sites,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "n_cols_left": n_cols_left,
        "n_cols_right": n_cols_right,
        "cluster_size": cluster_size,
        "cutoff_radius": cutoff_radius,
        "interface_axis": interface_axis,
        "interface_position": interface_position,
    }.items():
        if value is not None:
            payload[key] = value
    return payload


def _scenario(
    *,
    name: str,
    medium: dict[str, object],
    initial_site: int,
    trap_site: int,
    expectation: dict[str, str],
    coupling_hz: float = 1.0,
    sink_rate_hz: float = 0.65,
    loss_rate_hz: float = 0.02,
) -> dict[str, object]:
    return {
        "name": name,
        "coupling_hz": coupling_hz,
        "sink_rate_hz": sink_rate_hz,
        "loss_rate_hz": loss_rate_hz,
        "initial_site": initial_site,
        "trap_site": trap_site,
        "medium": medium,
        "literature_expectation": expectation,
    }


def _base_expectation(label: str) -> dict[str, str]:
    return _expectation(
        transport=f"{label}: clean coherent motion should be the reference, but geometry can make moderate phase scrambling useful.",
        disorder="Increasing local irregularity should usually reduce target arrival and increase ensemble-to-ensemble variability.",
        phase="Weak or moderate phase scrambling can help when coherent motion is trapped, but large values should suppress propagation.",
        failure="The expected failures are localization by irregularity, target-missing spread, or strong damping by excessive phase scrambling.",
    )


def _write_config(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _campaign_configs() -> list[tuple[str, Path, dict[str, object]]]:
    configs: list[tuple[str, Path, dict[str, object]]] = []

    r1_scenarios = [
        _scenario(
            name="R1 boundary 1D chain",
            medium=_medium("chain_1d", n_sites=10, interface_position=4.5),
            initial_site=9,
            trap_site=0,
            expectation=_base_expectation("1D chain"),
        ),
        _scenario(
            name="R1 boundary ring",
            medium=_medium("ring", n_sites=8, interface_position=0.0),
            initial_site=4,
            trap_site=0,
            expectation=_base_expectation("ring"),
        ),
        _scenario(
            name="R1 boundary 2D square",
            medium=_medium("square_lattice_2d", n_rows=4, n_cols=4, interface_position=1.5),
            initial_site=15,
            trap_site=0,
            expectation=_base_expectation("2D square lattice"),
        ),
    ]
    configs.append(
        (
            "R1 boundaries",
            ROOT / "configs" / "transport_research_rs_r1_boundaries.json",
            {
                "study_name": "R1 transport regime boundaries",
                "output_subdir": "medium_research_rs_r1_boundaries",
                "time_grid": {"t_final": 18.0, "n_samples": 240},
                "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
                "sweep": {
                    "disorder_strength_over_coupling": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                    "dephasing_over_coupling": [0.0, 0.02, 0.05, 0.08, 0.12, 0.2, 0.4, 0.8],
                },
                "ensemble_seeds": SEEDS_8,
                "scenarios": r1_scenarios,
            },
        )
    )

    r2_scenarios: list[dict[str, object]] = []
    for trap in [0, 4, 7]:
        r2_scenarios.append(
            _scenario(
                name=f"R2 target chain trap {trap}",
                medium=_medium("chain_1d", n_sites=10, interface_position=4.5),
                initial_site=9,
                trap_site=trap,
                expectation=_base_expectation("target placement in a chain"),
            )
        )
    for trap in [0, 1, 2, 3]:
        r2_scenarios.append(
            _scenario(
                name=f"R2 target ring trap {trap}",
                medium=_medium("ring", n_sites=8, interface_position=0.0),
                initial_site=4,
                trap_site=trap,
                expectation=_base_expectation("target placement in a ring"),
            )
        )
    for trap in [0, 3, 5, 10]:
        r2_scenarios.append(
            _scenario(
                name=f"R2 target 2D square trap {trap}",
                medium=_medium("square_lattice_2d", n_rows=4, n_cols=4, interface_position=1.5),
                initial_site=15,
                trap_site=trap,
                expectation=_base_expectation("target placement in a 2D sheet"),
            )
        )
    configs.append(
        (
            "R2 target placement",
            ROOT / "configs" / "transport_research_rs_r2_target_position.json",
            {
                "study_name": "R2 target-position sweep",
                "output_subdir": "medium_research_rs_r2_target_position",
                "time_grid": {"t_final": 18.0, "n_samples": 240},
                "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
                "sweep": {
                    "disorder_strength_over_coupling": [0.0, 0.4, 0.8],
                    "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.8],
                },
                "ensemble_seeds": SEEDS_8,
                "scenarios": r2_scenarios,
            },
        )
    )

    r3_scenarios = [
        _scenario(
            name="R3 robustness 1D chain",
            medium=_medium("chain_1d", n_sites=10, interface_position=4.5),
            initial_site=9,
            trap_site=0,
            expectation=_base_expectation("robustness of a chain"),
        ),
        _scenario(
            name="R3 robustness ring",
            medium=_medium("ring", n_sites=8, interface_position=0.0),
            initial_site=4,
            trap_site=0,
            expectation=_base_expectation("robustness of a ring"),
        ),
        _scenario(
            name="R3 robustness 2D square",
            medium=_medium("square_lattice_2d", n_rows=4, n_cols=4, interface_position=1.5),
            initial_site=15,
            trap_site=0,
            expectation=_base_expectation("robustness of a 2D sheet"),
        ),
    ]
    configs.append(
        (
            "R3 robustness",
            ROOT / "configs" / "transport_research_rs_r3_robustness.json",
            {
                "study_name": "R3 robustness to static irregularity",
                "output_subdir": "medium_research_rs_r3_robustness",
                "time_grid": {"t_final": 18.0, "n_samples": 240},
                "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
                "sweep": {
                    "disorder_strength_over_coupling": [0.0, 0.4, 0.8, 1.0],
                    "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.8],
                },
                "ensemble_seeds": SEEDS_32,
                "scenarios": r3_scenarios,
            },
        )
    )

    r4_scenarios = [
        _scenario(
            name="R4 molecular-wire-like chain",
            medium=_medium("chain_1d", n_sites=8, coupling_law="nearest_neighbor", interface_position=3.5),
            initial_site=7,
            trap_site=0,
            expectation=_base_expectation("molecular-wire-like chain"),
        ),
        _scenario(
            name="R4 ring aggregate",
            medium=_medium("ring", n_sites=8, coupling_law="nearest_neighbor", interface_position=0.0),
            initial_site=4,
            trap_site=0,
            expectation=_base_expectation("ring aggregate"),
        ),
        _scenario(
            name="R4 disordered 2D excitonic sheet",
            medium=_medium("square_lattice_2d", n_rows=3, n_cols=3, coupling_law="nearest_neighbor", interface_position=1.0),
            initial_site=8,
            trap_site=0,
            expectation=_base_expectation("2D excitonic sheet"),
        ),
        _scenario(
            name="R4 bottleneck medium",
            medium=_medium("bottleneck_lattice", n_rows=2, n_cols_left=2, n_cols_right=2, interface_position=2.0),
            initial_site=7,
            trap_site=0,
            expectation=_base_expectation("bottleneck medium"),
        ),
        _scenario(
            name="R4 clustered medium",
            medium=_medium("clustered_lattice", cluster_size=2, interface_position=2.0),
            initial_site=7,
            trap_site=0,
            expectation=_base_expectation("clustered medium"),
        ),
    ]
    configs.append(
        (
            "R4 material-inspired media",
            ROOT / "configs" / "transport_research_rs_r4_materials.json",
            {
                "study_name": "R4 material-inspired effective media",
                "output_subdir": "medium_research_rs_r4_materials",
                "time_grid": {"t_final": 18.0, "n_samples": 240},
                "thresholds": {"sink_hit_threshold": 0.1, "transfer_threshold": 0.5},
                "sweep": {
                    "disorder_strength_over_coupling": [0.0, 0.5, 0.9],
                    "dephasing_over_coupling": [0.0, 0.05, 0.2, 0.6],
                },
                "ensemble_seeds": SEEDS_8[:4],
                "scenarios": r4_scenarios,
            },
        )
    )
    return configs


def _run_campaign(config_path: Path, *, output_subdir: str, skip_existing: bool) -> None:
    result_path = ROOT / "outputs" / "transport_networks" / output_subdir / "latest" / "results.json"
    if skip_existing and result_path.exists():
        return
    command = [sys.executable, str(ROOT / "scripts" / "run_transport_medium_campaign.py"), "--config", str(config_path)]
    subprocess.run(command, cwd=ROOT, check=True)


def _load_results(output_subdir: str) -> dict[str, object]:
    return json.loads((ROOT / "outputs" / "transport_networks" / output_subdir / "latest" / "results.json").read_text(encoding="utf-8"))


def _best_indices(payload: dict[str, object]) -> tuple[int, int]:
    efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
    return tuple(int(v) for v in np.unravel_index(int(np.nanargmax(efficiency)), efficiency.shape))


def _max_phase_gain(payload: dict[str, object]) -> float:
    efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
    coherent = efficiency[:, 0]
    best_per_disorder = np.max(efficiency, axis=1)
    return float(np.max(best_per_disorder - coherent))


def _best_std(payload: dict[str, object]) -> float:
    row, col = _best_indices(payload)
    return float(np.asarray(payload["efficiency_std"], dtype=float)[row, col])


def _short_name(name: str) -> str:
    return name.replace("R1 boundary ", "").replace("R2 target ", "").replace("R3 robustness ", "").replace("R4 ", "")


def _collect_campaign_rows(campaign_payloads: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for campaign_key, results in campaign_payloads.items():
        for scenario in results["scenarios"]:
            best = scenario["best_point"]
            row, col = _best_indices(scenario)
            disorder_axis = np.asarray(scenario["disorder_strength_over_coupling"], dtype=float)
            dephasing_axis = np.asarray(scenario["dephasing_over_coupling"], dtype=float)
            efficiency = np.asarray(scenario["efficiency_mean"], dtype=float)
            efficiency_std = np.asarray(scenario["efficiency_std"], dtype=float)
            high_disorder_row = int(len(disorder_axis) - 1)
            high_disorder_col = int(np.nanargmax(efficiency[high_disorder_row]))
            rows.append(
                {
                    "campaign": campaign_key,
                    "scenario": str(scenario["scenario_name"]),
                    "short_scenario": _short_name(str(scenario["scenario_name"])),
                    "best_efficiency": float(best["transport_efficiency"]),
                    "best_disorder": float(best["disorder_over_coupling"]),
                    "best_dephasing": float(best["dephasing_over_coupling"]),
                    "best_regime": str(best["regime"]),
                    "best_spreading": float(best["spreading"]),
                    "best_mixing": float(best["mixing"]),
                    "best_std": _best_std(scenario),
                    "max_phase_gain": _max_phase_gain(scenario),
                    "realizations_at_best": int(np.asarray(scenario["realizations_used"], dtype=int)[row, col]),
                    "high_disorder": float(disorder_axis[high_disorder_row]),
                    "high_disorder_best_efficiency": float(efficiency[high_disorder_row, high_disorder_col]),
                    "high_disorder_best_std": float(efficiency_std[high_disorder_row, high_disorder_col]),
                    "high_disorder_best_dephasing": float(dephasing_axis[high_disorder_col]),
                }
            )
    return rows


def _plot_r1(output_path: Path, rows: list[dict[str, object]]) -> None:
    data = [row for row in rows if row["campaign"] == "R1"]
    labels = [str(row["short_scenario"]) for row in data]
    x = np.arange(len(data))
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.4), constrained_layout=True)
    axes[0].bar(x, [float(row["best_efficiency"]) for row in data], color="#2563eb")
    axes[0].set_title("best target arrival")
    axes[0].set_ylabel("final target population")
    axes[1].bar(x, [float(row["max_phase_gain"]) for row in data], color="#16a34a")
    axes[1].set_title("largest gain from phase scrambling")
    axes[1].set_ylabel("gain over zero scrambling")
    axes[2].bar(x, [float(row["best_dephasing"]) for row in data], color="#f97316")
    axes[2].set_title("best phase-scrambling strength")
    axes[2].set_ylabel("relative rate")
    axes[2].set_ylim(0.0, max(0.05, 1.18 * max(float(row["best_dephasing"]) for row in data)))
    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=25, ha="right")
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("R1: regime-boundary campaign", fontsize=15, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_r2(output_path: Path, rows: list[dict[str, object]]) -> None:
    data = [row for row in rows if row["campaign"] == "R2"]
    labels = [str(row["short_scenario"]) for row in data]
    x = np.arange(len(data))
    fig, axes = plt.subplots(2, 1, figsize=(13.0, 7.8), sharex=True, constrained_layout=True)
    axes[0].bar(x, [float(row["best_efficiency"]) for row in data], color="#0f766e")
    axes[0].set_ylabel("final target population")
    axes[0].set_title("target placement changes how much reaches the target")
    axes[1].bar(x, [float(row["best_dephasing"]) for row in data], color="#7c3aed")
    axes[1].set_ylabel("best relative phase-scrambling rate")
    axes[1].set_title("target placement also changes the best environment strength")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=35, ha="right")
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("R2: target-position campaign", fontsize=15, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_r3(output_path: Path, rows: list[dict[str, object]]) -> None:
    data = [row for row in rows if row["campaign"] == "R3"]
    labels = [str(row["short_scenario"]) for row in data]
    x = np.arange(len(data))
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), constrained_layout=True)
    axes[0].errorbar(
        x,
        [float(row["high_disorder_best_efficiency"]) for row in data],
        yerr=[float(row["high_disorder_best_std"]) for row in data],
        fmt="o",
        color="#2563eb",
        ecolor="#94a3b8",
        capsize=5,
    )
    axes[0].set_ylabel("target arrival at strongest tested irregularity")
    axes[0].set_title("best phase choice under strong disorder")
    axes[1].bar(x, [float(row["high_disorder_best_std"]) for row in data], color="#dc2626")
    axes[1].set_ylabel("ensemble spread under strong disorder")
    axes[1].set_title("lower spread means more robust")
    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=25, ha="right")
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("R3: robustness campaign", fontsize=15, weight="bold")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_r4(output_path: Path, rows: list[dict[str, object]]) -> None:
    data = [row for row in rows if row["campaign"] == "R4"]
    labels = [str(row["short_scenario"]) for row in data]
    x = np.arange(len(data))
    spread = np.asarray([float(row["best_spreading"]) for row in data], dtype=float)
    spread_norm = spread / max(float(np.max(spread)), 1e-12)
    mixing = np.asarray([float(row["best_mixing"]) for row in data], dtype=float)
    mixing_norm = mixing / max(float(np.max(mixing)), 1e-12)
    width = 0.25
    fig, axis = plt.subplots(figsize=(13.5, 6.2), constrained_layout=False)
    axis.bar(x - width, [float(row["best_efficiency"]) for row in data], width=width, color="#2563eb", label="target arrival")
    axis.bar(x, spread_norm, width=width, color="#16a34a", label="spreading normalized")
    axis.bar(x + width, mixing_norm, width=width, color="#f97316", label="mixing normalized")
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=30, ha="right")
    axis.set_ylabel("relative scale")
    axis.set_title("material-inspired media: arrival, spreading, and mixing are different quantities")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0.0, 1.18))
    fig.suptitle("R4: material-inspired effective media", fontsize=15, weight="bold", y=0.99)
    fig.subplots_adjust(top=0.78, bottom=0.30, left=0.08, right=0.98)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_rs_summary(output_dir: Path, rows: list[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "literature_check.json").write_text(json.dumps(LITERATURE_CHECK, indent=2), encoding="utf-8")
    (output_dir / "research_rs_summary.json").write_text(json.dumps({"rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# R1-R4 transport research campaign summary",
        "",
        f"Generated at UTC: {datetime.now(UTC).isoformat()}",
        "",
        "## Literature guardrails",
        "",
        "Google Scholar, ORCID and Lattes-like profile pages are useful for finding people and publication trails, but the physical criteria below are checked against primary papers and publisher pages.",
    ]
    for item in LITERATURE_CHECK:
        lines.append(f"- {item['key']}: {item['url']} -- {item['use']}")
    lines.extend(
        [
            "",
            "## Best points",
            "",
            "| campaign | scenario | best arrival | best irregularity | best phase scrambling | spread at best | regime |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['campaign']} | {row['scenario']} | {row['best_efficiency']:.3f} | {row['best_disorder']:.2f} | "
            f"{row['best_dephasing']:.2f} | {row['best_std']:.3f} | {row['best_regime']} |"
        )
    (output_dir / "research_rs_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the R1-R4 transport research campaigns and aggregate their dashboards.")
    parser.add_argument(
        "--rerun-existing",
        action="store_true",
        help="Rerun campaigns even when their results.json already exists.",
    )
    args = parser.parse_args(argv)

    configs = _campaign_configs()
    for _, path, payload in configs:
        _write_config(path, payload)
        _run_campaign(path, output_subdir=str(payload["output_subdir"]), skip_existing=not args.rerun_existing)

    campaign_payloads = {
        "R1": _load_results("medium_research_rs_r1_boundaries"),
        "R2": _load_results("medium_research_rs_r2_target_position"),
        "R3": _load_results("medium_research_rs_r3_robustness"),
        "R4": _load_results("medium_research_rs_r4_materials"),
    }
    rows = _collect_campaign_rows(campaign_payloads)
    output_dir = ROOT / "outputs" / "transport_networks" / "research_rs" / "latest"
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    _plot_r1(figure_dir / "r1_regime_boundaries_summary.png", rows)
    _plot_r2(figure_dir / "r2_target_position_summary.png", rows)
    _plot_r3(figure_dir / "r3_robustness_summary.png", rows)
    _plot_r4(figure_dir / "r4_material_inspired_summary.png", rows)
    _write_rs_summary(output_dir, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
