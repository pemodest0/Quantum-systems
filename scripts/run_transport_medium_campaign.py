from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.lines import Line2D
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport import (  # noqa: E402
    build_medium_campaign_review,
    build_medium_definition,
    classify_regime,
    load_medium_campaign_config,
    review_bundle_to_dict,
)

from oqs_transport.simulation import simulate_transport  # noqa: E402


REGIME_ORDER = [
    "coherent-dominated",
    "dephasing-assisted",
    "localized-by-disorder",
    "loss-dominated",
    "strongly-damped",
    "mixed-crossover",
]

REGIME_COLORS = {
    "coherent-dominated": "#0f766e",
    "dephasing-assisted": "#65a30d",
    "localized-by-disorder": "#f59e0b",
    "loss-dominated": "#dc2626",
    "strongly-damped": "#7c3aed",
    "mixed-crossover": "#64748b",
}


def _safe_script_label() -> str:
    try:
        return str(Path(__file__).resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return "scripts/run_transport_medium_campaign.py"


def _axis_index(label: str | None) -> int | None:
    if label is None:
        return None
    mapping = {"x": 0, "y": 1}
    if label not in mapping:
        raise ValueError(f"unsupported interface axis: {label}")
    return mapping[label]


def _dump_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, np.floating):
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def _nanmean(values: list[float | None]) -> float | None:
    numeric = np.asarray([np.nan if value is None else float(value) for value in values], dtype=float)
    if np.all(np.isnan(numeric)):
        return None
    return float(np.nanmean(numeric))


def _nanstd(values: list[float | None]) -> float | None:
    numeric = np.asarray([np.nan if value is None else float(value) for value in values], dtype=float)
    if np.all(np.isnan(numeric)):
        return None
    return float(np.nanstd(numeric, ddof=0))


def _scenario_title(name: str) -> str:
    return name.replace(" medium", "").replace("Medium", "medium")


def _draw_medium_geometry(
    output_path: Path,
    geometry_payloads: list[dict[str, object]],
) -> None:
    n_panels = len(geometry_payloads)
    fig, axes = plt.subplots(1, n_panels, figsize=(5.2 * n_panels, 4.6), constrained_layout=True)
    if n_panels == 1:
        axes = np.array([axes])
    for axis, payload in zip(axes, geometry_payloads, strict=True):
        coordinates = np.asarray(payload["coordinates"], dtype=float)
        adjacency = np.asarray(payload["adjacency"], dtype=float)
        initial_site = int(payload["initial_site"])
        trap_site = int(payload["trap_site"])
        for i in range(adjacency.shape[0]):
            for j in range(i + 1, adjacency.shape[1]):
                if adjacency[i, j] > 0.0:
                    axis.plot(
                        [coordinates[i, 0], coordinates[j, 0]],
                        [coordinates[i, 1], coordinates[j, 1]],
                        color="#cbd5e1",
                        lw=1.6,
                        zorder=1,
                    )
        axis.scatter(coordinates[:, 0], coordinates[:, 1], s=170, color="#0f172a", edgecolors="white", linewidths=1.2, zorder=2)
        axis.scatter(
            coordinates[initial_site, 0],
            coordinates[initial_site, 1],
            s=240,
            color="#2563eb",
            edgecolors="white",
            linewidths=1.5,
            zorder=3,
        )
        axis.scatter(
            coordinates[trap_site, 0],
            coordinates[trap_site, 1],
            s=240,
            color="#dc2626",
            edgecolors="white",
            linewidths=1.5,
            zorder=3,
        )
        for idx, (x_coord, y_coord) in enumerate(coordinates):
            axis.text(x_coord, y_coord, str(idx), ha="center", va="center", color="white", fontsize=9, zorder=4)
        axis.set_title(str(payload["scenario_name"]))
        axis.set_aspect("equal")
        axis.axis("off")
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#0f172a", markersize=10, label="physical site"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2563eb", markersize=10, label="initial site"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#dc2626", markersize=10, label="target site"),
    ]
    fig.suptitle("Medium geometries used in campaign A", y=1.02)
    fig.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_metric_maps(
    output_path: Path,
    scenario_payloads: list[dict[str, object]],
    *,
    metric_key: str,
    title: str,
    colorbar_label: str,
    annotate_best: bool = False,
) -> None:
    n_panels = len(scenario_payloads)
    fig, axes = plt.subplots(1, n_panels, figsize=(5.8 * n_panels, 4.6), sharey=True, constrained_layout=True)
    if n_panels == 1:
        axes = np.array([axes])
    color_mappable = None
    for axis, payload in zip(axes, scenario_payloads, strict=True):
        data = np.asarray(payload[metric_key], dtype=float)
        image = axis.imshow(data, origin="lower", aspect="auto", cmap="viridis")
        color_mappable = image
        disorder_ticks = np.arange(len(payload["disorder_strength_over_coupling"]))
        dephasing_ticks = np.arange(len(payload["dephasing_over_coupling"]))
        axis.set_xticks(dephasing_ticks)
        axis.set_xticklabels([f"{value:.2f}" for value in payload["dephasing_over_coupling"]], rotation=45, ha="right")
        axis.set_yticks(disorder_ticks)
        axis.set_yticklabels([f"{value:.2f}" for value in payload["disorder_strength_over_coupling"]])
        axis.set_title(_scenario_title(str(payload["scenario_name"])))
        axis.set_xlabel("phase scrambling / coherent coupling")
        if annotate_best:
            best_index = np.unravel_index(int(np.nanargmax(data)), data.shape)
            axis.scatter(best_index[1], best_index[0], marker="x", color="white", s=90, linewidths=2.0)
    axes[0].set_ylabel("local irregularity / coherent coupling")
    fig.suptitle(title, y=0.98)
    if color_mappable is not None:
        colorbar = fig.colorbar(color_mappable, ax=axes.ravel().tolist(), shrink=0.90)
        colorbar.set_label(colorbar_label)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_regime_maps(output_path: Path, scenario_payloads: list[dict[str, object]]) -> None:
    n_panels = len(scenario_payloads)
    fig, axes = plt.subplots(1, n_panels, figsize=(5.8 * n_panels, 4.8), sharey=True, constrained_layout=True)
    if n_panels == 1:
        axes = np.array([axes])
    cmap = colors.ListedColormap([REGIME_COLORS[label] for label in REGIME_ORDER])
    norm = colors.BoundaryNorm(np.arange(len(REGIME_ORDER) + 1) - 0.5, len(REGIME_ORDER))
    color_mappable = None
    for axis, payload in zip(axes, scenario_payloads, strict=True):
        label_grid = payload["regime_label_grid"]
        numeric_grid = np.array([[REGIME_ORDER.index(label) for label in row] for row in label_grid], dtype=float)
        image = axis.imshow(numeric_grid, origin="lower", aspect="auto", cmap=cmap, norm=norm)
        color_mappable = image
        disorder_ticks = np.arange(len(payload["disorder_strength_over_coupling"]))
        dephasing_ticks = np.arange(len(payload["dephasing_over_coupling"]))
        axis.set_xticks(dephasing_ticks)
        axis.set_xticklabels([f"{value:.2f}" for value in payload["dephasing_over_coupling"]], rotation=45, ha="right")
        axis.set_yticks(disorder_ticks)
        axis.set_yticklabels([f"{value:.2f}" for value in payload["disorder_strength_over_coupling"]])
        axis.set_title(_scenario_title(str(payload["scenario_name"])))
        axis.set_xlabel("phase scrambling / coherent coupling")
    axes[0].set_ylabel("local irregularity / coherent coupling")
    fig.suptitle("Regime classification maps", y=0.98)
    if color_mappable is not None:
        colorbar = fig.colorbar(color_mappable, ax=axes.ravel().tolist(), shrink=0.90, ticks=np.arange(len(REGIME_ORDER)))
        colorbar.ax.set_yticklabels(REGIME_ORDER)
        colorbar.set_label("regime label")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _expectation_assessment(
    *,
    efficiency_mean: np.ndarray,
    dephasing_over_coupling: np.ndarray,
) -> dict[str, object]:
    coherent_column = efficiency_mean[:, 0]
    row_best = np.max(efficiency_mean, axis=1)
    disorder_suppresses = bool(row_best[-1] < row_best[0] - 0.03)
    moderate_phase_helps = bool(np.any(row_best - coherent_column > 0.03) and np.any(dephasing_over_coupling[np.argmax(efficiency_mean, axis=1)] > 0.0))
    strong_phase_fails = bool(np.mean(efficiency_mean[:, -1]) < np.mean(row_best) - 0.03)
    score = float(np.mean([disorder_suppresses, moderate_phase_helps, strong_phase_fails]))
    return {
        "measured_disorder_suppresses_transport": disorder_suppresses,
        "measured_moderate_phase_scrambling_can_help": moderate_phase_helps,
        "measured_strong_phase_scrambling_suppresses_transport": strong_phase_fails,
        "agreement_score": score,
        "agreement_level": "high" if score >= 2 / 3 else "partial" if score >= 1 / 3 else "low",
    }


def _write_summary_tables(output_dir: Path, rows: list[dict[str, object]], expectation_rows: list[dict[str, object]]) -> None:
    table_dir = output_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "scenario_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    markdown_lines = [
        "| scenario | best success | best disorder/coupling | best phase scrambling/coupling | best regime | final spread | final mixing |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        markdown_lines.append(
            f"| {row['scenario']} | {float(row['best_efficiency']):.3f} | {float(row['best_disorder_over_coupling']):.2f} | "
            f"{float(row['best_dephasing_over_coupling']):.2f} | {row['best_regime']} | {float(row['best_spreading']):.3f} | {float(row['best_mixing']):.3f} |"
        )
    (table_dir / "scenario_summary.md").write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    expectation_lines = [
        "| scenario | disorder hurts | moderate phase helps | strong phase hurts | agreement score | agreement level |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in expectation_rows:
        expectation_lines.append(
            f"| {row['scenario']} | {row['disorder_suppresses']} | {row['moderate_phase_helps']} | {row['strong_phase_hurts']} | "
            f"{float(row['agreement_score']):.2f} | {row['agreement_level']} |"
        )
    (table_dir / "expectation_comparison.md").write_text("\n".join(expectation_lines) + "\n", encoding="utf-8")


def _build_medium_from_spec(scenario, disorder_strength_hz: float, seed: int | None):
    medium = scenario.medium
    coordinates = None
    if medium.coordinates is not None:
        coordinates = np.asarray(medium.coordinates, dtype=float)
    return build_medium_definition(
        medium_type=medium.medium_type,
        coupling_law=medium.coupling_law,
        length_scale=medium.length_scale,
        disorder_strength_hz=disorder_strength_hz,
        site_energy_profile=medium.site_energy_profile,
        coordinates=coordinates,
        seed=seed,
        n_sites=medium.n_sites,
        n_rows=medium.n_rows,
        n_cols=medium.n_cols,
        n_cols_left=medium.n_cols_left,
        n_cols_right=medium.n_cols_right,
        cluster_size=medium.cluster_size,
        gradient_strength_hz=medium.gradient_strength_hz,
        decay_length=medium.decay_length,
        power_law_exponent=medium.power_law_exponent,
        cutoff_radius=medium.cutoff_radius,
    )


def _metric_maps_from_realizations(
    scenario,
    disorder_axis: np.ndarray,
    dephasing_axis: np.ndarray,
    seeds: tuple[int, ...],
    times: np.ndarray,
    *,
    sink_hit_threshold: float,
    transfer_threshold: float,
) -> tuple[dict[str, object], dict[str, object]]:
    n_disorder = len(disorder_axis)
    n_dephasing = len(dephasing_axis)
    efficiency_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    efficiency_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    spreading_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    spreading_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    mixing_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    mixing_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    coherence_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    coherence_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    purity_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    purity_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    pop_entropy_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    pop_entropy_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    participation_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    participation_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    ipr_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    ipr_std = np.zeros((n_disorder, n_dephasing), dtype=float)
    sink_hit_mean = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    sink_hit_std = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    transfer_mean = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    transfer_std = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    interface_current_mean = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    interface_current_std = np.full((n_disorder, n_dephasing), np.nan, dtype=float)
    loss_mean = np.zeros((n_disorder, n_dephasing), dtype=float)
    diagnostics = {
        "max_trace_deviation": np.zeros((n_disorder, n_dephasing), dtype=float),
        "max_population_closure_error": np.zeros((n_disorder, n_dephasing), dtype=float),
        "min_state_eigenvalue": np.zeros((n_disorder, n_dephasing), dtype=float),
    }
    realizations_used = np.zeros((n_disorder, n_dephasing), dtype=int)

    representative_geometry: dict[str, object] | None = None

    for disorder_index, disorder_ratio in enumerate(disorder_axis):
        disorder_strength_hz = float(disorder_ratio) * float(scenario.coupling_hz)
        seeds_for_row = seeds if disorder_strength_hz > 0.0 else seeds[:1]
        for dephasing_index, dephasing_ratio in enumerate(dephasing_axis):
            dephasing_rate_hz = float(dephasing_ratio) * float(scenario.coupling_hz)
            efficiencies: list[float] = []
            spreading: list[float] = []
            mixing: list[float] = []
            coherences: list[float] = []
            purities: list[float] = []
            pop_entropies: list[float] = []
            participation_ratios: list[float] = []
            ipr_values: list[float] = []
            sink_hits: list[float | None] = []
            transfer_hits: list[float | None] = []
            interface_currents: list[float | None] = []
            losses: list[float] = []
            trace_deviations: list[float] = []
            closure_errors: list[float] = []
            min_eigenvalues: list[float] = []

            for seed in seeds_for_row:
                medium_definition = _build_medium_from_spec(scenario, disorder_strength_hz, seed)
                if representative_geometry is None:
                    representative_geometry = {
                        "scenario_name": scenario.name,
                        "coordinates": medium_definition.coordinates.tolist(),
                        "adjacency": medium_definition.adjacency.tolist(),
                        "initial_site": scenario.initial_site,
                        "trap_site": scenario.trap_site,
                    }
                result = simulate_transport(
                    adjacency=medium_definition.adjacency,
                    coupling_hz=scenario.coupling_hz,
                    dephasing_rate_hz=dephasing_rate_hz,
                    sink_rate_hz=scenario.sink_rate_hz,
                    loss_rate_hz=scenario.loss_rate_hz,
                    times=times,
                    initial_site=scenario.initial_site,
                    trap_site=scenario.trap_site,
                    site_energies_hz=medium_definition.site_energies_hz,
                    node_coordinates=medium_definition.coordinates,
                    sink_hit_threshold=sink_hit_threshold,
                    transfer_threshold=transfer_threshold,
                    interface_axis=_axis_index(scenario.medium.interface_axis),
                    interface_position=scenario.medium.interface_position,
                )
                efficiencies.append(result.transport_efficiency)
                spreading.append(float(result.mean_squared_displacement_t[-1]) if result.mean_squared_displacement_t is not None else 0.0)
                mixing.append(result.final_entropy)
                coherences.append(result.mean_coherence_l1)
                purities.append(result.final_purity)
                pop_entropies.append(result.final_population_shannon_entropy)
                participation_ratios.append(result.final_participation_ratio)
                ipr_values.append(result.final_ipr)
                sink_hits.append(result.sink_hitting_time)
                transfer_hits.append(result.transfer_time_to_threshold)
                interface_currents.append(result.integrated_interface_current)
                losses.append(float(result.loss_population[-1]))
                trace_deviations.append(result.max_trace_deviation)
                closure_errors.append(result.max_population_closure_error)
                min_eigenvalues.append(result.min_state_eigenvalue)

            realizations_used[disorder_index, dephasing_index] = len(seeds_for_row)
            efficiency_mean[disorder_index, dephasing_index] = float(np.mean(efficiencies))
            efficiency_std[disorder_index, dephasing_index] = float(np.std(efficiencies, ddof=0))
            spreading_mean[disorder_index, dephasing_index] = float(np.mean(spreading))
            spreading_std[disorder_index, dephasing_index] = float(np.std(spreading, ddof=0))
            mixing_mean[disorder_index, dephasing_index] = float(np.mean(mixing))
            mixing_std[disorder_index, dephasing_index] = float(np.std(mixing, ddof=0))
            coherence_mean[disorder_index, dephasing_index] = float(np.mean(coherences))
            coherence_std[disorder_index, dephasing_index] = float(np.std(coherences, ddof=0))
            purity_mean[disorder_index, dephasing_index] = float(np.mean(purities))
            purity_std[disorder_index, dephasing_index] = float(np.std(purities, ddof=0))
            pop_entropy_mean[disorder_index, dephasing_index] = float(np.mean(pop_entropies))
            pop_entropy_std[disorder_index, dephasing_index] = float(np.std(pop_entropies, ddof=0))
            participation_mean[disorder_index, dephasing_index] = float(np.mean(participation_ratios))
            participation_std[disorder_index, dephasing_index] = float(np.std(participation_ratios, ddof=0))
            ipr_mean[disorder_index, dephasing_index] = float(np.mean(ipr_values))
            ipr_std[disorder_index, dephasing_index] = float(np.std(ipr_values, ddof=0))
            sink_hit_mean_value = _nanmean(sink_hits)
            sink_hit_std_value = _nanstd(sink_hits)
            transfer_mean_value = _nanmean(transfer_hits)
            transfer_std_value = _nanstd(transfer_hits)
            interface_current_mean_value = _nanmean(interface_currents)
            interface_current_std_value = _nanstd(interface_currents)
            sink_hit_mean[disorder_index, dephasing_index] = np.nan if sink_hit_mean_value is None else sink_hit_mean_value
            sink_hit_std[disorder_index, dephasing_index] = np.nan if sink_hit_std_value is None else sink_hit_std_value
            transfer_mean[disorder_index, dephasing_index] = np.nan if transfer_mean_value is None else transfer_mean_value
            transfer_std[disorder_index, dephasing_index] = np.nan if transfer_std_value is None else transfer_std_value
            interface_current_mean[disorder_index, dephasing_index] = (
                np.nan if interface_current_mean_value is None else interface_current_mean_value
            )
            interface_current_std[disorder_index, dephasing_index] = (
                np.nan if interface_current_std_value is None else interface_current_std_value
            )
            loss_mean[disorder_index, dephasing_index] = float(np.mean(losses))
            diagnostics["max_trace_deviation"][disorder_index, dephasing_index] = float(np.max(trace_deviations))
            diagnostics["max_population_closure_error"][disorder_index, dephasing_index] = float(np.max(closure_errors))
            diagnostics["min_state_eigenvalue"][disorder_index, dephasing_index] = float(np.min(min_eigenvalues))

    regime_label_grid: list[list[str]] = []
    regime_confidence_grid: list[list[float]] = []
    regime_reason_codes_grid: list[list[list[str]]] = []
    for disorder_index, disorder_ratio in enumerate(disorder_axis):
        coherent_reference = float(efficiency_mean[disorder_index, 0])
        best_efficiency_reference = float(np.max(efficiency_mean[disorder_index]))
        max_spreading_reference = float(np.max(spreading_mean[disorder_index]))
        row_labels: list[str] = []
        row_confidences: list[float] = []
        row_reasons: list[list[str]] = []
        for dephasing_index, dephasing_ratio in enumerate(dephasing_axis):
            classification = classify_regime(
                transport_efficiency=float(efficiency_mean[disorder_index, dephasing_index]),
                coherent_efficiency_reference=coherent_reference,
                best_efficiency_reference=best_efficiency_reference,
                final_loss_population=float(loss_mean[disorder_index, dephasing_index]),
                disorder_strength_over_coupling=float(disorder_ratio),
                dephasing_over_coupling=float(dephasing_ratio),
                mean_coherence_l1=float(coherence_mean[disorder_index, dephasing_index]),
                final_participation_ratio=float(participation_mean[disorder_index, dephasing_index]),
                final_entropy=float(mixing_mean[disorder_index, dephasing_index]),
                final_mean_squared_displacement=float(spreading_mean[disorder_index, dephasing_index]),
                max_mean_squared_displacement_reference=max_spreading_reference,
                n_sites=int(len(representative_geometry["coordinates"])) if representative_geometry is not None else 1,
            )
            row_labels.append(classification.label)
            row_confidences.append(classification.confidence)
            row_reasons.append(list(classification.reason_codes))
        regime_label_grid.append(row_labels)
        regime_confidence_grid.append(row_confidences)
        regime_reason_codes_grid.append(row_reasons)

    best_flat_index = np.unravel_index(int(np.argmax(efficiency_mean)), efficiency_mean.shape)
    expectation_assessment = _expectation_assessment(
        efficiency_mean=efficiency_mean,
        dephasing_over_coupling=dephasing_axis,
    )

    scenario_payload = {
        "scenario_name": scenario.name,
        "medium_type": scenario.medium.medium_type,
        "n_sites": int(len(representative_geometry["coordinates"])) if representative_geometry is not None else scenario.medium.n_sites,
        "coupling_hz": float(scenario.coupling_hz),
        "sink_rate_hz": float(scenario.sink_rate_hz),
        "loss_rate_hz": float(scenario.loss_rate_hz),
        "initial_site": int(scenario.initial_site),
        "trap_site": int(scenario.trap_site),
        "disorder_strength_over_coupling": disorder_axis.tolist(),
        "dephasing_over_coupling": dephasing_axis.tolist(),
        "coordinates": None if representative_geometry is None else representative_geometry["coordinates"],
        "adjacency": None if representative_geometry is None else representative_geometry["adjacency"],
        "efficiency_mean": efficiency_mean.tolist(),
        "efficiency_std": efficiency_std.tolist(),
        "spreading_mean": spreading_mean.tolist(),
        "spreading_std": spreading_std.tolist(),
        "mixing_mean": mixing_mean.tolist(),
        "mixing_std": mixing_std.tolist(),
        "coherence_mean": coherence_mean.tolist(),
        "coherence_std": coherence_std.tolist(),
        "purity_mean": purity_mean.tolist(),
        "purity_std": purity_std.tolist(),
        "population_entropy_mean": pop_entropy_mean.tolist(),
        "population_entropy_std": pop_entropy_std.tolist(),
        "participation_ratio_mean": participation_mean.tolist(),
        "participation_ratio_std": participation_std.tolist(),
        "ipr_mean": ipr_mean.tolist(),
        "ipr_std": ipr_std.tolist(),
        "sink_hitting_time_mean": _json_ready(sink_hit_mean),
        "sink_hitting_time_std": _json_ready(sink_hit_std),
        "transfer_time_mean": _json_ready(transfer_mean),
        "transfer_time_std": _json_ready(transfer_std),
        "integrated_interface_current_mean": _json_ready(interface_current_mean),
        "integrated_interface_current_std": _json_ready(interface_current_std),
        "loss_mean": loss_mean.tolist(),
        "diagnostics": _json_ready(diagnostics),
        "realizations_used": realizations_used.tolist(),
        "regime_label_grid": regime_label_grid,
        "regime_confidence_grid": regime_confidence_grid,
        "regime_reason_codes_grid": regime_reason_codes_grid,
        "best_point": {
            "disorder_over_coupling": float(disorder_axis[best_flat_index[0]]),
            "dephasing_over_coupling": float(dephasing_axis[best_flat_index[1]]),
            "transport_efficiency": float(efficiency_mean[best_flat_index]),
            "spreading": float(spreading_mean[best_flat_index]),
            "mixing": float(mixing_mean[best_flat_index]),
            "regime": regime_label_grid[best_flat_index[0]][best_flat_index[1]],
        },
        "literature_expectation": asdict(scenario.literature_expectation),
        "expectation_assessment": expectation_assessment,
    }
    summary_row = {
        "scenario": scenario.name,
        "best_efficiency": float(efficiency_mean[best_flat_index]),
        "best_disorder_over_coupling": float(disorder_axis[best_flat_index[0]]),
        "best_dephasing_over_coupling": float(dephasing_axis[best_flat_index[1]]),
        "best_regime": regime_label_grid[best_flat_index[0]][best_flat_index[1]],
        "best_spreading": float(spreading_mean[best_flat_index]),
        "best_mixing": float(mixing_mean[best_flat_index]),
    }
    return scenario_payload, {"geometry": representative_geometry, "summary_row": summary_row}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the first medium-propagation campaign.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_medium_campaign_config.json"),
        help="Path to the medium campaign configuration file.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    config = load_medium_campaign_config(config_path)
    output_dir = ROOT / "outputs" / "transport_networks" / config.output_subdir / "latest"
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    times = np.linspace(0.0, config.t_final, config.n_time_samples)
    scenario_payloads: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    expectation_rows: list[dict[str, object]] = []
    geometry_payloads: list[dict[str, object]] = []
    regime_counts: dict[str, int] = {label: 0 for label in REGIME_ORDER}

    for scenario in config.scenarios:
        scenario_payload, aux = _metric_maps_from_realizations(
            scenario,
            disorder_axis=config.disorder_strength_over_coupling,
            dephasing_axis=config.dephasing_over_coupling,
            seeds=config.ensemble_seeds,
            times=times,
            sink_hit_threshold=config.sink_hit_threshold,
            transfer_threshold=config.transfer_threshold,
        )
        scenario_payloads.append(scenario_payload)
        summary_rows.append(aux["summary_row"])
        geometry_payloads.append(aux["geometry"])
        expectation_assessment = scenario_payload["expectation_assessment"]
        expectation_rows.append(
            {
                "scenario": scenario.name,
                "disorder_suppresses": expectation_assessment["measured_disorder_suppresses_transport"],
                "moderate_phase_helps": expectation_assessment["measured_moderate_phase_scrambling_can_help"],
                "strong_phase_hurts": expectation_assessment["measured_strong_phase_scrambling_suppresses_transport"],
                "agreement_score": expectation_assessment["agreement_score"],
                "agreement_level": expectation_assessment["agreement_level"],
            }
        )
        for row in scenario_payload["regime_label_grid"]:
            for label in row:
                regime_counts[label] = regime_counts.get(label, 0) + 1

    _draw_medium_geometry(figure_dir / "medium_geometry_overview.png", geometry_payloads)
    _plot_metric_maps(
        figure_dir / "transport_success_maps.png",
        scenario_payloads,
        metric_key="efficiency_mean",
        title="Transport success maps",
        colorbar_label="final target population",
        annotate_best=True,
    )
    _plot_metric_maps(
        figure_dir / "spreading_maps.png",
        scenario_payloads,
        metric_key="spreading_mean",
        title="Spreading maps",
        colorbar_label="final mean squared displacement",
    )
    _plot_metric_maps(
        figure_dir / "mixing_maps.png",
        scenario_payloads,
        metric_key="mixing_mean",
        title="Mixing maps",
        colorbar_label="final graph-normalized entropy",
    )
    _plot_regime_maps(figure_dir / "regime_maps.png", scenario_payloads)

    transport_values = [float(value) for payload in scenario_payloads for row in payload["efficiency_mean"] for value in row]
    spreading_values = [float(value) for payload in scenario_payloads for row in payload["spreading_mean"] for value in row]
    mixing_values = [float(value) for payload in scenario_payloads for row in payload["mixing_mean"] for value in row]
    review_bundle = build_medium_campaign_review(
        scenario_names=[str(payload["scenario_name"]) for payload in scenario_payloads],
        transport_range=(float(min(transport_values)), float(max(transport_values))),
        spreading_range=(float(min(spreading_values)), float(max(spreading_values))),
        mixing_range=(float(min(mixing_values)), float(max(mixing_values))),
        regime_counts=regime_counts,
    )
    review_payload = review_bundle_to_dict(review_bundle)

    _write_summary_tables(output_dir, summary_rows, expectation_rows)

    results_payload = {
        "study_name": config.study_name,
        "campaign_type": "medium_propagation",
        "times": {"t_final": float(times[-1]), "n_samples": int(times.size)},
        "scenarios": scenario_payloads,
    }
    metrics_payload = {
        "scenario_best_points": summary_rows,
        "regime_counts": regime_counts,
        "transport_range": [float(min(transport_values)), float(max(transport_values))],
        "spreading_range": [float(min(spreading_values)), float(max(spreading_values))],
        "mixing_range": [float(min(mixing_values)), float(max(mixing_values))],
        "planner_next_action": review_payload["planner"],
    }
    config_used = {
        "study_name": config.study_name,
        "output_subdir": config.output_subdir,
        "time_grid": {"t_final": config.t_final, "n_samples": config.n_time_samples},
        "thresholds": {
            "sink_hit_threshold": config.sink_hit_threshold,
            "transfer_threshold": config.transfer_threshold,
        },
        "sweep": {
            "disorder_strength_over_coupling": config.disorder_strength_over_coupling.tolist(),
            "dephasing_over_coupling": config.dephasing_over_coupling.tolist(),
        },
        "ensemble_seeds": list(config.ensemble_seeds),
        "scenarios": [
            {
                "name": scenario.name,
                "coupling_hz": scenario.coupling_hz,
                "sink_rate_hz": scenario.sink_rate_hz,
                "loss_rate_hz": scenario.loss_rate_hz,
                "initial_site": scenario.initial_site,
                "trap_site": scenario.trap_site,
                "medium": asdict(scenario.medium),
                "literature_expectation": asdict(scenario.literature_expectation),
            }
            for scenario in config.scenarios
        ],
    }
    run_metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "script": _safe_script_label(),
        "config_path": str(config_path),
        "output_dir": str(output_dir.relative_to(ROOT)),
    }

    _dump_json(output_dir / "results.json", _json_ready(results_payload))
    _dump_json(output_dir / "metrics.json", _json_ready(metrics_payload))
    _dump_json(output_dir / "config_used.json", _json_ready(config_used))
    _dump_json(output_dir / "run_metadata.json", _json_ready(run_metadata))
    _dump_json(output_dir / "analyst_review.json", _json_ready(review_payload))
    _dump_json(output_dir / "figure_explanations_ptbr.json", _json_ready(review_payload["figure_explanations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
