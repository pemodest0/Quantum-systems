from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import (  # noqa: E402
    generate_network_instance,
    mean_std_sem_ci95,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
)
from scripts.run_transport_methodological_benchmarks import _weighted_instance  # noqa: E402


METRIC_KEYS = (
    "arrival",
    "gain_vs_zero_dephasing",
    "loss_population",
    "network_population",
    "mean_coherence_l1",
    "final_purity",
    "final_entropy",
    "population_shannon_entropy",
    "participation_ratio",
    "ipr",
    "sink_hitting_time_filled",
)


def profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {
            "profile": "smoke",
            "family": "modular_two_community",
            "edge_model": "unweighted",
            "n_sites_values": [8],
            "graph_realizations": 2,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 7100,
            "disorder_strength_over_coupling": [0.5, 0.6],
            "dephasing_over_coupling": [0.0, 0.8, 1.2, 1.6],
            "target_style": "near",
            "t_final": 10.0,
            "n_time_samples": 72,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    if profile == "paper":
        return {
            "profile": "paper",
            "family": "modular_two_community",
            "edge_model": "unweighted",
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 6,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23],
            "graph_seed_base": 7200,
            "disorder_strength_over_coupling": [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80],
            "dephasing_over_coupling": [0.0, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0],
            "target_style": "near",
            "t_final": 16.0,
            "n_time_samples": 120,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _group_key(row: dict[str, object], keys: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(row.get(key, "")) for key in keys)


def _add_gain_against_zero(rows: list[dict[str, object]]) -> None:
    baselines: dict[tuple[str, str, str, str, str], float] = {}
    for row in rows:
        if abs(float(row["dephasing_over_coupling"])) < 1e-12:
            key = (
                str(row["n_sites"]),
                str(row["graph_seed"]),
                str(row["disorder_seed"]),
                str(row["disorder_strength_over_coupling"]),
                str(row["trap_site"]),
            )
            baselines[key] = float(row["arrival"])
    for row in rows:
        key = (
            str(row["n_sites"]),
            str(row["graph_seed"]),
            str(row["disorder_seed"]),
            str(row["disorder_strength_over_coupling"]),
            str(row["trap_site"]),
        )
        row["zero_dephasing_arrival"] = baselines.get(key, float(row["arrival"]))
        row["gain_vs_zero_dephasing"] = float(row["arrival"]) - float(row["zero_dephasing_arrival"])


def _aggregate_curves(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    group_keys = ("disorder_strength_over_coupling", "dephasing_over_coupling")
    for row in rows:
        grouped[_group_key(row, group_keys)].append(row)
    output: list[dict[str, object]] = []
    for key, items in sorted(grouped.items(), key=lambda item: (float(item[0][0]), float(item[0][1]))):
        out: dict[str, object] = {name: value for name, value in zip(group_keys, key, strict=False)}
        for metric in METRIC_KEYS:
            summary = mean_std_sem_ci95(float(item[metric]) for item in items)
            for summary_key, summary_value in summary.items():
                out[f"{metric}_{summary_key}"] = summary_value
        output.append(out)
    return output


def _detect_peaks(stat_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_w: dict[float, list[dict[str, object]]] = defaultdict(list)
    for row in stat_rows:
        by_w[float(row["disorder_strength_over_coupling"])].append(row)
    diagnostics: list[dict[str, object]] = []
    for disorder, items in sorted(by_w.items()):
        ordered = sorted(items, key=lambda row: float(row["dephasing_over_coupling"]))
        gammas = np.asarray([float(row["dephasing_over_coupling"]) for row in ordered], dtype=float)
        arrivals = np.asarray([float(row["arrival_mean"]) for row in ordered], dtype=float)
        gains = np.asarray([float(row["gain_vs_zero_dephasing_mean"]) for row in ordered], dtype=float)
        local_peaks: list[float] = []
        for index in range(1, len(arrivals) - 1):
            prominence = arrivals[index] - max(arrivals[index - 1], arrivals[index + 1])
            if arrivals[index] > arrivals[index - 1] and arrivals[index] > arrivals[index + 1] and prominence >= 0.01:
                local_peaks.append(float(gammas[index]))
        best_index = int(np.argmax(arrivals))
        high_dephasing_penalty = float(arrivals[best_index] - arrivals[-1])
        diagnostics.append(
            {
                "disorder_strength_over_coupling": disorder,
                "best_dephasing_over_coupling": float(gammas[best_index]),
                "best_arrival_mean": float(arrivals[best_index]),
                "best_gain_mean": float(gains[best_index]),
                "high_dephasing_penalty": high_dephasing_penalty,
                "local_peak_count": len(local_peaks),
                "local_peak_gammas": local_peaks,
                "curve_shape": "two_peak_candidate" if len(local_peaks) >= 2 else ("single_peak" if local_peaks else "monotone_or_plateau"),
            }
        )
    return diagnostics


def _matrix_from_stats(stat_rows: list[dict[str, object]], metric: str) -> tuple[np.ndarray, list[float], list[float]]:
    disorders = sorted({float(row["disorder_strength_over_coupling"]) for row in stat_rows})
    gammas = sorted({float(row["dephasing_over_coupling"]) for row in stat_rows})
    matrix = np.full((len(disorders), len(gammas)), np.nan)
    lookup = {
        (float(row["disorder_strength_over_coupling"]), float(row["dephasing_over_coupling"])): float(row[metric])
        for row in stat_rows
    }
    for i, disorder in enumerate(disorders):
        for j, gamma in enumerate(gammas):
            matrix[i, j] = lookup.get((disorder, gamma), np.nan)
    return matrix, disorders, gammas


def _plot_curves(stat_rows: list[dict[str, object]], *, metric: str, ylabel: str, title: str, output_path: Path) -> None:
    by_w: dict[float, list[dict[str, object]]] = defaultdict(list)
    for row in stat_rows:
        by_w[float(row["disorder_strength_over_coupling"])].append(row)
    fig, ax = plt.subplots(figsize=(9.0, 5.2), constrained_layout=True)
    cmap = plt.get_cmap("viridis")
    disorders = sorted(by_w)
    for index, disorder in enumerate(disorders):
        ordered = sorted(by_w[disorder], key=lambda row: float(row["dephasing_over_coupling"]))
        x = np.asarray([float(row["dephasing_over_coupling"]) for row in ordered], dtype=float)
        y = np.asarray([float(row[f"{metric}_mean"]) for row in ordered], dtype=float)
        low = np.asarray([float(row[f"{metric}_ci95_low"]) for row in ordered], dtype=float)
        high = np.asarray([float(row[f"{metric}_ci95_high"]) for row in ordered], dtype=float)
        color = cmap(index / max(len(disorders) - 1, 1))
        ax.plot(x, y, marker="o", linewidth=1.8, label=f"W/J={disorder:.2f}", color=color)
        ax.fill_between(x, low, high, color=color, alpha=0.16)
    ax.set_title(title)
    ax.set_xlabel("phase scrambling rate / coherent coupling")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_heatmap(stat_rows: list[dict[str, object]], *, metric: str, title: str, colorbar_label: str, output_path: Path) -> None:
    matrix, disorders, gammas = _matrix_from_stats(stat_rows, f"{metric}_mean")
    fig, ax = plt.subplots(figsize=(9.0, 5.4), constrained_layout=True)
    im = ax.imshow(matrix, aspect="auto", origin="lower", cmap="magma" if metric == "arrival" else "coolwarm")
    ax.set_title(title)
    ax.set_xlabel("phase scrambling rate / coherent coupling")
    ax.set_ylabel("local irregularity / coherent coupling")
    ax.set_xticks(np.arange(len(gammas)))
    ax.set_xticklabels([f"{value:.2f}" for value in gammas], rotation=30, ha="right")
    ax.set_yticks(np.arange(len(disorders)))
    ax.set_yticklabels([f"{value:.2f}" for value in disorders])
    fig.colorbar(im, ax=ax, label=colorbar_label)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_peak_diagnostics(peak_rows: list[dict[str, object]], output_path: Path) -> None:
    disorders = [float(row["disorder_strength_over_coupling"]) for row in peak_rows]
    best_gamma = [float(row["best_dephasing_over_coupling"]) for row in peak_rows]
    penalty = [float(row["high_dephasing_penalty"]) for row in peak_rows]
    fig, ax1 = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax1.plot(disorders, best_gamma, marker="o", color="#1565c0", label="best phase scrambling")
    ax1.set_xlabel("local irregularity / coherent coupling")
    ax1.set_ylabel("best phase scrambling / coherent coupling", color="#1565c0")
    ax1.tick_params(axis="y", labelcolor="#1565c0")
    ax2 = ax1.twinx()
    ax2.plot(disorders, penalty, marker="s", color="#c62828", label="high-scrambling penalty")
    ax2.set_ylabel("best arrival - high-scrambling arrival", color="#c62828")
    ax2.tick_params(axis="y", labelcolor="#c62828")
    ax1.grid(alpha=0.25)
    ax1.set_title("Peak and high-scrambling diagnostics")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(output_dir: Path, metrics: dict[str, object], peak_rows: list[dict[str, object]]) -> None:
    strongest = max(peak_rows, key=lambda row: float(row["best_gain_mean"])) if peak_rows else {}
    two_peak_candidates = [row for row in peak_rows if int(row["local_peak_count"]) >= 2]
    lines = [
        "# Modular Refinement Campaign",
        "",
        "## Scientific Question",
        "",
        "Does the modular two-community network keep a real dephasing-assisted transport window when the disorder and phase-scrambling grid is refined?",
        "",
        "## Plain Reading",
        "",
        "- `W/J` means local irregularity compared with coherent hopping strength.",
        "- `gamma/J` means phase scrambling compared with coherent hopping strength.",
        "- `arrival` means final population captured by the successful-arrival channel.",
        "- `gain` means arrival at a given phase scrambling minus arrival with zero phase scrambling for the same graph and disorder realization.",
        "",
        "## Main Numerical Result",
        "",
        f"- Simulated curve points: {metrics.get('curve_record_count', 0)}.",
        f"- Numerical validation passed: {metrics.get('numerics_pass', False)}.",
        f"- Strongest mean gain: {float(metrics.get('strongest_gain_mean', 0.0)):.3f}.",
        f"- Strongest disorder `W/J`: {strongest.get('disorder_strength_over_coupling', 'unknown')}.",
        f"- Strongest phase scrambling `gamma/J`: {strongest.get('best_dephasing_over_coupling', 'unknown')}.",
        f"- Two-peak candidates found: {len(two_peak_candidates)}.",
        "",
        "## Interpretation",
        "",
        "The result is strong only if the gain is positive with a positive confidence interval and the high-scrambling end does not simply keep improving forever.",
        "",
        "## Next Action",
        "",
        "If the best point sits at the upper gamma boundary, extend the gamma grid. If it is internal and stable, use this as the refined modular-network claim.",
        "",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _copy_latest(output_dir: Path, latest_dir: Path) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        target = latest_dir / path.name
        if path.is_dir():
            target.mkdir(exist_ok=True)
            for child in path.iterdir():
                if child.is_file():
                    (target / child.name).write_bytes(child.read_bytes())
        elif path.is_file():
            target.write_bytes(path.read_bytes())


def run_campaign(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    rows: list[dict[str, object]] = []
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    coupling = float(config["coupling_hz"])

    for n_sites in list(config["n_sites_values"]):
        for realization in range(int(config["graph_realizations"])):
            graph_seed = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * realization
            base = generate_network_instance(str(config["family"]), n_sites=int(n_sites), seed=graph_seed, realization_index=realization)
            instance = _weighted_instance(base, str(config["edge_model"]))
            initial_site = int(n_sites) - 1
            trap_site = int(target_candidates(instance, initial_site=initial_site)[str(config["target_style"])])
            topo = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
            for disorder_strength in list(config["disorder_strength_over_coupling"]):
                for disorder_seed in list(config["disorder_seeds"]):
                    seed = int(disorder_seed) + 17 * graph_seed + int(round(1000 * float(disorder_strength)))
                    site_energies = static_disorder_energies(int(n_sites), float(disorder_strength) * coupling, seed=seed)
                    for gamma in list(config["dephasing_over_coupling"]):
                        result = simulate_transport(
                            adjacency=instance.adjacency,
                            coupling_hz=coupling,
                            dephasing_rate_hz=float(gamma) * coupling,
                            sink_rate_hz=float(config["sink_rate_hz"]),
                            loss_rate_hz=float(config["loss_rate_hz"]),
                            times=times,
                            initial_site=initial_site,
                            trap_site=trap_site,
                            site_energies_hz=site_energies,
                            node_coordinates=instance.coordinates,
                            sink_hit_threshold=0.1,
                            transfer_threshold=0.5,
                        )
                        t_final = float(result.times[-1])
                        row: dict[str, object] = {
                            "family": str(config["family"]),
                            "edge_model": str(config["edge_model"]),
                            "instance_id": instance.instance_id,
                            "n_sites": int(n_sites),
                            "graph_seed": graph_seed,
                            "realization": realization,
                            "disorder_seed": int(disorder_seed),
                            "disorder_strength_over_coupling": float(disorder_strength),
                            "dephasing_over_coupling": float(gamma),
                            "target_style": str(config["target_style"]),
                            "initial_site": initial_site,
                            "trap_site": trap_site,
                            "arrival": float(result.transport_efficiency),
                            "loss_population": float(result.loss_population[-1]),
                            "network_population": float(result.network_population[-1]),
                            "mean_coherence_l1": float(result.mean_coherence_l1),
                            "final_purity": float(result.final_purity),
                            "final_entropy": float(result.final_entropy),
                            "population_shannon_entropy": float(result.final_population_shannon_entropy),
                            "participation_ratio": float(result.final_participation_ratio),
                            "ipr": float(result.final_ipr),
                            "final_msd": 0.0 if result.mean_squared_displacement_t is None else float(result.mean_squared_displacement_t[-1]),
                            "final_front_width": 0.0 if result.front_width_t is None else float(result.front_width_t[-1]),
                            "sink_hitting_time_filled": t_final if result.sink_hitting_time is None else float(result.sink_hitting_time),
                            "transfer_time_filled": t_final if result.transfer_time_to_threshold is None else float(result.transfer_time_to_threshold),
                            "max_trace_deviation": float(result.max_trace_deviation),
                            "max_population_closure_error": float(result.max_population_closure_error),
                            "min_state_eigenvalue": float(result.min_state_eigenvalue),
                        }
                        row.update({f"topology_{key}": float(value) for key, value in topo.items()})
                        rows.append(row)
                        validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(result.max_trace_deviation))
                        validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(result.max_population_closure_error))
                        validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(result.min_state_eigenvalue))

    _add_gain_against_zero(rows)
    stat_rows = _aggregate_curves(rows)
    peak_rows = _detect_peaks(stat_rows)
    strongest = max(peak_rows, key=lambda row: float(row["best_gain_mean"])) if peak_rows else {}
    numerics_pass = bool(
        validation["max_trace_deviation"] < 1e-8
        and validation["max_population_closure_error"] < 1e-8
        and validation["min_state_eigenvalue"] > -1e-7
    )
    metrics = {
        "profile": config["profile"],
        "curve_record_count": len(rows),
        "curve_stat_count": len(stat_rows),
        "validation": validation,
        "numerics_pass": numerics_pass,
        "strongest_gain_mean": float(strongest.get("best_gain_mean", 0.0)) if strongest else 0.0,
        "strongest_point": strongest,
        "two_peak_candidate_count": sum(1 for row in peak_rows if int(row["local_peak_count"]) >= 2),
    }

    _write_csv(rows, output_dir / "gamma_curve_records.csv")
    _write_csv(stat_rows, output_dir / "gamma_curve_statistics.csv")
    (output_dir / "gamma_curve_records.json").write_text(json.dumps({"rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "gamma_curve_statistics.json").write_text(json.dumps({"rows": stat_rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "peak_diagnostics.json").write_text(json.dumps({"rows": peak_rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "profile": config["profile"]}, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_summary(output_dir, metrics, peak_rows)

    _plot_curves(stat_rows, metric="arrival", ylabel="arrival at target", title="Full transport curves for the modular network", output_path=figures_dir / "arrival_vs_phase_scrambling_curves.png")
    _plot_curves(stat_rows, metric="gain_vs_zero_dephasing", ylabel="arrival gain over zero scrambling", title="Noise-assistance curves for the modular network", output_path=figures_dir / "gain_vs_phase_scrambling_curves.png")
    _plot_heatmap(stat_rows, metric="arrival", title="Target arrival map", colorbar_label="mean arrival at target", output_path=figures_dir / "arrival_w_gamma_heatmap.png")
    _plot_heatmap(stat_rows, metric="gain_vs_zero_dephasing", title="Noise-assistance gain map", colorbar_label="mean gain over zero scrambling", output_path=figures_dir / "gain_w_gamma_heatmap.png")
    _plot_peak_diagnostics(peak_rows, figures_dir / "peak_diagnostics.png")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run refined full-curve campaign for modular two-community open transport.")
    parser.add_argument("--profile", choices=["smoke", "paper"], default="paper")
    parser.add_argument("--output-subdir", default="modular_refinement")
    args = parser.parse_args(argv)
    config = profile_config(args.profile)
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / args.profile
    latest_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = run_campaign(config, output_dir)
    _copy_latest(output_dir, latest_dir)
    print(json.dumps({"output_dir": str(output_dir), "latest_dir": str(latest_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
