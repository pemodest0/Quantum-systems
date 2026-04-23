from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np

from .campaigns import MediumCampaignConfig
from .mediums import build_medium_definition
from .simulation import TransportSimulationResult, simulate_transport


@dataclass(frozen=True)
class VisualCaseSpec:
    scenario_name: str
    label: str
    disorder_over_coupling: float
    dephasing_over_coupling: float
    representative_seed: int | None
    representative_efficiency: float
    ensemble_mean_efficiency: float
    ensemble_std_efficiency: float


def load_campaign_results(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _scenario_lookup(config: MediumCampaignConfig) -> dict[str, object]:
    return {scenario.name: scenario for scenario in config.scenarios}


def _cell_value(payload: dict[str, object], row: int, col: int) -> float:
    return float(np.asarray(payload["efficiency_mean"], dtype=float)[row, col])


def _row_col_to_case(
    *,
    payload: dict[str, object],
    label: str,
    row: int,
    col: int,
    representative_seed: int | None,
    representative_efficiency: float,
    std_efficiency: float,
) -> VisualCaseSpec:
    disorder_axis = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
    dephasing_axis = np.asarray(payload["dephasing_over_coupling"], dtype=float)
    return VisualCaseSpec(
        scenario_name=str(payload["scenario_name"]),
        label=label,
        disorder_over_coupling=float(disorder_axis[row]),
        dephasing_over_coupling=float(dephasing_axis[col]),
        representative_seed=representative_seed,
        representative_efficiency=representative_efficiency,
        ensemble_mean_efficiency=float(np.asarray(payload["efficiency_mean"], dtype=float)[row, col]),
        ensemble_std_efficiency=std_efficiency,
    )


def choose_representative_seed(
    *,
    scenario,
    disorder_over_coupling: float,
    dephasing_over_coupling: float,
    seeds: tuple[int, ...],
    times: np.ndarray,
    sink_hit_threshold: float,
    transfer_threshold: float,
    target_mean_efficiency: float,
) -> tuple[int | None, float]:
    disorder_strength_hz = float(disorder_over_coupling) * float(scenario.coupling_hz)
    seeds_to_check = seeds if disorder_strength_hz > 0.0 else seeds[:1]
    if not seeds_to_check:
        return None, target_mean_efficiency
    axis_map = {"x": 0, "y": 1}
    best_seed: int | None = None
    best_efficiency = target_mean_efficiency
    best_distance = float("inf")
    for seed in seeds_to_check:
        medium = build_medium_definition(
            medium_type=scenario.medium.medium_type,
            coupling_law=scenario.medium.coupling_law,
            length_scale=scenario.medium.length_scale,
            disorder_strength_hz=disorder_strength_hz,
            site_energy_profile=scenario.medium.site_energy_profile,
            coordinates=None if scenario.medium.coordinates is None else np.asarray(scenario.medium.coordinates, dtype=float),
            seed=seed,
            n_sites=scenario.medium.n_sites,
            n_rows=scenario.medium.n_rows,
            n_cols=scenario.medium.n_cols,
            n_cols_left=scenario.medium.n_cols_left,
            n_cols_right=scenario.medium.n_cols_right,
            cluster_size=scenario.medium.cluster_size,
            gradient_strength_hz=scenario.medium.gradient_strength_hz,
            decay_length=scenario.medium.decay_length,
            power_law_exponent=scenario.medium.power_law_exponent,
            cutoff_radius=scenario.medium.cutoff_radius,
        )
        result = simulate_transport(
            adjacency=medium.adjacency,
            coupling_hz=scenario.coupling_hz,
            dephasing_rate_hz=float(dephasing_over_coupling) * float(scenario.coupling_hz),
            sink_rate_hz=scenario.sink_rate_hz,
            loss_rate_hz=scenario.loss_rate_hz,
            times=times,
            initial_site=scenario.initial_site,
            trap_site=scenario.trap_site,
            site_energies_hz=medium.site_energies_hz,
            node_coordinates=medium.coordinates,
            sink_hit_threshold=sink_hit_threshold,
            transfer_threshold=transfer_threshold,
            interface_axis=axis_map.get(scenario.medium.interface_axis) if scenario.medium.interface_axis is not None else None,
            interface_position=scenario.medium.interface_position,
        )
        distance = abs(result.transport_efficiency - target_mean_efficiency)
        if distance < best_distance:
            best_distance = distance
            best_seed = int(seed)
            best_efficiency = float(result.transport_efficiency)
    return best_seed, best_efficiency


def build_visual_case_specs(
    *,
    config: MediumCampaignConfig,
    results_payload: dict[str, object],
) -> dict[str, list[VisualCaseSpec]]:
    scenario_map = _scenario_lookup(config)
    times = np.linspace(0.0, config.t_final, config.n_time_samples)
    specs: dict[str, list[VisualCaseSpec]] = {}
    for payload in results_payload["scenarios"]:
        efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
        std_efficiency = np.asarray(payload["efficiency_std"], dtype=float)
        best_row, best_col = np.unravel_index(int(np.argmax(efficiency)), efficiency.shape)
        worst_row, worst_col = np.unravel_index(int(np.argmin(efficiency)), efficiency.shape)
        scenario = scenario_map[str(payload["scenario_name"])]
        best_seed, best_rep_eff = choose_representative_seed(
            scenario=scenario,
            disorder_over_coupling=float(np.asarray(payload["disorder_strength_over_coupling"], dtype=float)[best_row]),
            dephasing_over_coupling=float(np.asarray(payload["dephasing_over_coupling"], dtype=float)[best_col]),
            seeds=config.ensemble_seeds,
            times=times,
            sink_hit_threshold=config.sink_hit_threshold,
            transfer_threshold=config.transfer_threshold,
            target_mean_efficiency=float(efficiency[best_row, best_col]),
        )
        worst_seed, worst_rep_eff = choose_representative_seed(
            scenario=scenario,
            disorder_over_coupling=float(np.asarray(payload["disorder_strength_over_coupling"], dtype=float)[worst_row]),
            dephasing_over_coupling=float(np.asarray(payload["dephasing_over_coupling"], dtype=float)[worst_col]),
            seeds=config.ensemble_seeds,
            times=times,
            sink_hit_threshold=config.sink_hit_threshold,
            transfer_threshold=config.transfer_threshold,
            target_mean_efficiency=float(efficiency[worst_row, worst_col]),
        )
        specs[str(payload["scenario_name"])] = [
            _row_col_to_case(
                payload=payload,
                label="best",
                row=best_row,
                col=best_col,
                representative_seed=best_seed,
                representative_efficiency=best_rep_eff,
                std_efficiency=float(std_efficiency[best_row, best_col]),
            ),
            _row_col_to_case(
                payload=payload,
                label="worst",
                row=worst_row,
                col=worst_col,
                representative_seed=worst_seed,
                representative_efficiency=worst_rep_eff,
                std_efficiency=float(std_efficiency[worst_row, worst_col]),
            ),
        ]
    return specs


def rerun_visual_case(
    *,
    config: MediumCampaignConfig,
    scenario_name: str,
    case_spec: VisualCaseSpec,
) -> tuple[TransportSimulationResult, np.ndarray, np.ndarray]:
    scenario = _scenario_lookup(config)[scenario_name]
    times = np.linspace(0.0, config.t_final, config.n_time_samples)
    disorder_strength_hz = float(case_spec.disorder_over_coupling) * float(scenario.coupling_hz)
    medium = build_medium_definition(
        medium_type=scenario.medium.medium_type,
        coupling_law=scenario.medium.coupling_law,
        length_scale=scenario.medium.length_scale,
        disorder_strength_hz=disorder_strength_hz,
        site_energy_profile=scenario.medium.site_energy_profile,
        coordinates=None if scenario.medium.coordinates is None else np.asarray(scenario.medium.coordinates, dtype=float),
        seed=case_spec.representative_seed,
        n_sites=scenario.medium.n_sites,
        n_rows=scenario.medium.n_rows,
        n_cols=scenario.medium.n_cols,
        n_cols_left=scenario.medium.n_cols_left,
        n_cols_right=scenario.medium.n_cols_right,
        cluster_size=scenario.medium.cluster_size,
        gradient_strength_hz=scenario.medium.gradient_strength_hz,
        decay_length=scenario.medium.decay_length,
        power_law_exponent=scenario.medium.power_law_exponent,
        cutoff_radius=scenario.medium.cutoff_radius,
    )
    axis_map = {"x": 0, "y": 1}
    result = simulate_transport(
        adjacency=medium.adjacency,
        coupling_hz=scenario.coupling_hz,
        dephasing_rate_hz=float(case_spec.dephasing_over_coupling) * float(scenario.coupling_hz),
        sink_rate_hz=scenario.sink_rate_hz,
        loss_rate_hz=scenario.loss_rate_hz,
        times=times,
        initial_site=scenario.initial_site,
        trap_site=scenario.trap_site,
        site_energies_hz=medium.site_energies_hz,
        node_coordinates=medium.coordinates,
        sink_hit_threshold=config.sink_hit_threshold,
        transfer_threshold=config.transfer_threshold,
        interface_axis=axis_map.get(scenario.medium.interface_axis) if scenario.medium.interface_axis is not None else None,
        interface_position=scenario.medium.interface_position,
    )
    return result, medium.coordinates, medium.adjacency


def _draw_network_state(
    axis: plt.Axes,
    *,
    title: str,
    coordinates: np.ndarray,
    adjacency: np.ndarray,
    populations: np.ndarray,
    initial_site: int,
    trap_site: int,
    sink_value: float,
    loss_value: float,
    x_limits: tuple[float, float],
    y_limits: tuple[float, float],
) -> None:
    norm = Normalize(vmin=0.0, vmax=max(0.35, float(np.max(populations))))
    for i in range(adjacency.shape[0]):
        for j in range(i + 1, adjacency.shape[1]):
            if adjacency[i, j] > 0.0:
                axis.plot(
                    [coordinates[i, 0], coordinates[j, 0]],
                    [coordinates[i, 1], coordinates[j, 1]],
                    color="#cbd5e1",
                    lw=1.4,
                    alpha=0.9,
                    zorder=1,
                )
    colors = cm.plasma(norm(populations))
    sizes = 230 + 2200 * np.clip(populations, 0.0, 1.0)
    edgecolors = []
    linewidths = []
    for node in range(adjacency.shape[0]):
        if node == trap_site:
            edgecolors.append("#dc2626")
            linewidths.append(2.8)
        elif node == initial_site:
            edgecolors.append("#2563eb")
            linewidths.append(2.8)
        else:
            edgecolors.append("#0f172a")
            linewidths.append(1.2)
    axis.scatter(coordinates[:, 0], coordinates[:, 1], s=sizes, c=colors, edgecolors=edgecolors, linewidths=linewidths, zorder=2)
    for idx, (x_coord, y_coord) in enumerate(coordinates):
        axis.text(x_coord, y_coord, str(idx), ha="center", va="center", color="white", fontsize=9, zorder=3)
    axis.set_title(title, pad=10)
    axis.set_aspect("equal")
    axis.set_xlim(*x_limits)
    axis.set_ylim(*y_limits)
    axis.axis("off")


def _coordinate_limits(coordinates: np.ndarray) -> tuple[tuple[float, float], tuple[float, float]]:
    x_min = float(np.min(coordinates[:, 0]))
    x_max = float(np.max(coordinates[:, 0]))
    y_min = float(np.min(coordinates[:, 1]))
    y_max = float(np.max(coordinates[:, 1]))
    span = max(x_max - x_min, y_max - y_min, 1.0)
    pad = 0.18 * span
    return (x_min - pad, x_max + pad), (y_min - pad, y_max + pad)


def _draw_header_card(
    axis: plt.Axes,
    *,
    scenario_name: str,
    time_value: float,
    best_case: VisualCaseSpec,
    worst_case: VisualCaseSpec,
    best_result: TransportSimulationResult,
    worst_result: TransportSimulationResult,
    frame: int,
) -> None:
    axis.clear()
    axis.axis("off")
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.text(
        0.02,
        0.88,
        f"{scenario_name}: live best-vs-worst comparison",
        ha="left",
        va="top",
        fontsize=15,
        weight="bold",
        color="#0f172a",
    )
    axis.text(
        0.02,
        0.58,
        f"time = {time_value:.2f}",
        ha="left",
        va="top",
        fontsize=11.5,
        color="#334155",
    )
    axis.text(
        0.02,
        0.32,
        (
            "best case\n"
            f"irregularity / coupling = {best_case.disorder_over_coupling:.2f}\n"
            f"phase scrambling / coupling = {best_case.dephasing_over_coupling:.2f}\n"
            f"target population = {best_result.sink_population[frame]:.3f}\n"
            f"loss population = {best_result.loss_population[frame]:.3f}"
        ),
        ha="left",
        va="top",
        fontsize=9.6,
        color="#0f172a",
        bbox={"boxstyle": "round", "fc": "#f8fafc", "ec": "#94a3b8", "alpha": 0.98},
    )
    axis.text(
        0.53,
        0.32,
        (
            "worst case\n"
            f"irregularity / coupling = {worst_case.disorder_over_coupling:.2f}\n"
            f"phase scrambling / coupling = {worst_case.dephasing_over_coupling:.2f}\n"
            f"target population = {worst_result.sink_population[frame]:.3f}\n"
            f"loss population = {worst_result.loss_population[frame]:.3f}"
        ),
        ha="left",
        va="top",
        fontsize=9.6,
        color="#0f172a",
        bbox={"boxstyle": "round", "fc": "#f8fafc", "ec": "#94a3b8", "alpha": 0.98},
    )


def _surface_value_from_best_point(best_payload: dict[str, object], metric_key: str) -> float:
    if metric_key == "efficiency_mean":
        return float(best_payload["transport_efficiency"])
    if metric_key == "spreading_mean":
        return float(best_payload["spreading"])
    return float(best_payload["mixing"])


def render_case_comparison_gif(
    output_path: Path,
    *,
    scenario_name: str,
    best_case: VisualCaseSpec,
    worst_case: VisualCaseSpec,
    best_result: TransportSimulationResult,
    best_coordinates: np.ndarray,
    best_adjacency: np.ndarray,
    worst_result: TransportSimulationResult,
    worst_coordinates: np.ndarray,
    worst_adjacency: np.ndarray,
    initial_site: int,
    trap_site: int,
    stride: int = 4,
    fps: int = 10,
) -> None:
    frame_indices = list(range(0, len(best_result.times), max(1, stride)))
    if frame_indices[-1] != len(best_result.times) - 1:
        frame_indices.append(len(best_result.times) - 1)

    fig = plt.figure(figsize=(12.2, 7.4))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.2, 3.0, 1.5], hspace=0.28, wspace=0.10)
    ax_header = fig.add_subplot(grid[0, :])
    ax_best = fig.add_subplot(grid[1, 0])
    ax_worst = fig.add_subplot(grid[1, 1])
    ax_series = fig.add_subplot(grid[2, :])

    best_x_limits, best_y_limits = _coordinate_limits(best_coordinates)
    worst_x_limits, worst_y_limits = _coordinate_limits(worst_coordinates)
    max_series_value = float(
        max(
            np.max(best_result.sink_population),
            np.max(worst_result.sink_population),
            np.max(best_result.loss_population),
            np.max(worst_result.loss_population),
            0.05,
        )
    )

    def _draw(frame_number: int) -> None:
        frame = frame_indices[frame_number]
        _draw_header_card(
            ax_header,
            scenario_name=scenario_name,
            time_value=float(best_result.times[frame]),
            best_case=best_case,
            worst_case=worst_case,
            best_result=best_result,
            worst_result=worst_result,
            frame=frame,
        )
        ax_best.clear()
        ax_worst.clear()
        ax_series.clear()
        _draw_network_state(
            ax_best,
            title="best case",
            coordinates=best_coordinates,
            adjacency=best_adjacency,
            populations=best_result.node_populations[frame],
            initial_site=initial_site,
            trap_site=trap_site,
            sink_value=float(best_result.sink_population[frame]),
            loss_value=float(best_result.loss_population[frame]),
            x_limits=best_x_limits,
            y_limits=best_y_limits,
        )
        _draw_network_state(
            ax_worst,
            title="worst case",
            coordinates=worst_coordinates,
            adjacency=worst_adjacency,
            populations=worst_result.node_populations[frame],
            initial_site=initial_site,
            trap_site=trap_site,
            sink_value=float(worst_result.sink_population[frame]),
            loss_value=float(worst_result.loss_population[frame]),
            x_limits=worst_x_limits,
            y_limits=worst_y_limits,
        )

        ax_series.plot(best_result.times[: frame + 1], best_result.sink_population[: frame + 1], color="#16a34a", lw=2.2, label="best target")
        ax_series.plot(worst_result.times[: frame + 1], worst_result.sink_population[: frame + 1], color="#dc2626", lw=2.2, label="worst target")
        ax_series.plot(best_result.times[: frame + 1], best_result.loss_population[: frame + 1], color="#0f172a", lw=1.4, ls="--", label="best loss")
        ax_series.plot(worst_result.times[: frame + 1], worst_result.loss_population[: frame + 1], color="#7f1d1d", lw=1.4, ls="--", label="worst loss")
        ax_series.axvline(best_result.times[frame], color="#64748b", lw=1.0, ls=":")
        ax_series.set_xlabel("time")
        ax_series.set_ylabel("population")
        ax_series.set_title("target capture and loss versus time", pad=16)
        ax_series.set_xlim(float(best_result.times[0]), float(best_result.times[-1]))
        ax_series.set_ylim(0.0, 1.06 * max_series_value)
        ax_series.grid(alpha=0.2)
        ax_series.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.22))

    fig.subplots_adjust(top=0.96, bottom=0.08, left=0.05, right=0.98)

    animation = FuncAnimation(fig, _draw, frames=len(frame_indices), interval=max(50, int(1000 / max(1, fps))), repeat=True)
    animation.save(output_path, writer=PillowWriter(fps=max(1, fps)))
    plt.close(fig)


def render_surface_figure(
    output_path: Path,
    *,
    scenario_payloads: list[dict[str, object]],
    metric_key: str,
    title: str,
    z_label: str,
    elev: float = 28.0,
    azim: float = -60.0,
) -> None:
    fig = plt.figure(figsize=(6.2 * len(scenario_payloads), 5.8))
    grid = fig.add_gridspec(2, len(scenario_payloads), height_ratios=[0.22, 0.78], hspace=0.02, wspace=0.20)
    ax_header = fig.add_subplot(grid[0, :])
    ax_header.axis("off")
    ax_header.text(0.0, 0.92, title, ha="left", va="top", fontsize=15, weight="bold", color="#0f172a")
    ax_header.text(
        0.0,
        0.52,
        "Horizontal axis: phase scrambling compared with coherent coupling. "
        "Depth axis: irregularity compared with coherent coupling. Height: measured quantity.",
        ha="left",
        va="top",
        fontsize=9.5,
        color="#334155",
    )
    all_values = np.concatenate([np.ravel(np.asarray(payload[metric_key], dtype=float)) for payload in scenario_payloads])
    norm = Normalize(vmin=float(np.min(all_values)), vmax=float(np.max(all_values)))
    for index, payload in enumerate(scenario_payloads, start=1):
        ax = fig.add_subplot(grid[1, index - 1], projection="3d")
        x_axis = np.asarray(payload["dephasing_over_coupling"], dtype=float)
        y_axis = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
        x_grid, y_grid = np.meshgrid(x_axis, y_axis)
        z_grid = np.asarray(payload[metric_key], dtype=float)
        face_colors = cm.viridis(norm(z_grid))
        ax.plot_surface(x_grid, y_grid, z_grid, facecolors=face_colors, linewidth=0.5, edgecolor="#94a3b8", antialiased=True, shade=False)
        best = payload["best_point"]
        ax.scatter(
            [float(best["dephasing_over_coupling"])],
            [float(best["disorder_over_coupling"])],
            [_surface_value_from_best_point(best, metric_key)],
            color="crimson",
            s=50,
            depthshade=False,
        )
        ax.text2D(0.5, 0.94, str(payload["scenario_name"]).replace(" medium", ""), transform=ax.transAxes, ha="center", va="top", fontsize=13)
        ax.set_xlabel("phase scrambling / coupling")
        ax.set_ylabel("irregularity / coupling")
        ax.set_zlabel(z_label)
        ax.view_init(elev=elev, azim=azim)
    mappable = cm.ScalarMappable(norm=norm, cmap="viridis")
    mappable.set_array([])
    fig.colorbar(mappable, ax=fig.axes, shrink=0.72, pad=0.04, label=z_label)
    fig.subplots_adjust(top=0.95, bottom=0.04, left=0.04, right=0.97)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def render_surface_rotation_gif(
    output_path: Path,
    *,
    scenario_payloads: list[dict[str, object]],
    metric_key: str,
    title: str,
    z_label: str,
    frames: int = 24,
) -> None:
    fig = plt.figure(figsize=(6.2 * len(scenario_payloads), 5.8))
    grid = fig.add_gridspec(2, len(scenario_payloads), height_ratios=[0.22, 0.78], hspace=0.02, wspace=0.20)
    ax_header = fig.add_subplot(grid[0, :])
    ax_header.axis("off")
    axes = [fig.add_subplot(grid[1, index], projection="3d") for index in range(len(scenario_payloads))]
    all_values = np.concatenate([np.ravel(np.asarray(payload[metric_key], dtype=float)) for payload in scenario_payloads])
    norm = Normalize(vmin=float(np.min(all_values)), vmax=float(np.max(all_values)))

    def _draw(frame_number: int) -> None:
        azimuth = -70.0 + 140.0 * frame_number / max(frames - 1, 1)
        ax_header.clear()
        ax_header.axis("off")
        ax_header.text(0.0, 0.92, f"{title}: rotating view", ha="left", va="top", fontsize=15, weight="bold", color="#0f172a")
        ax_header.text(
            0.0,
            0.52,
            "Same data as the static surface. Only the camera angle changes, so peaks and valleys can be inspected without text overlap.",
            ha="left",
            va="top",
            fontsize=9.5,
            color="#334155",
        )
        for ax, payload in zip(axes, scenario_payloads, strict=True):
            ax.clear()
            x_axis = np.asarray(payload["dephasing_over_coupling"], dtype=float)
            y_axis = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
            x_grid, y_grid = np.meshgrid(x_axis, y_axis)
            z_grid = np.asarray(payload[metric_key], dtype=float)
            face_colors = cm.viridis(norm(z_grid))
            ax.plot_surface(x_grid, y_grid, z_grid, facecolors=face_colors, linewidth=0.5, edgecolor="#94a3b8", antialiased=True, shade=False)
            best = payload["best_point"]
            ax.scatter(
                [float(best["dephasing_over_coupling"])],
                [float(best["disorder_over_coupling"])],
                [_surface_value_from_best_point(best, metric_key)],
                color="crimson",
                s=55,
                depthshade=False,
            )
            ax.text2D(0.5, 0.94, str(payload["scenario_name"]).replace(" medium", ""), transform=ax.transAxes, ha="center", va="top", fontsize=13)
            ax.set_xlabel("phase scrambling / coupling")
            ax.set_ylabel("irregularity / coupling")
            ax.set_zlabel(z_label)
            ax.view_init(elev=28.0, azim=azimuth)
        fig.subplots_adjust(top=0.95, bottom=0.04, left=0.04, right=0.97)

    animation = FuncAnimation(fig, _draw, frames=frames, interval=120, repeat=True)
    animation.save(output_path, writer=PillowWriter(fps=10))
    plt.close(fig)


def _load_gif_frames(path: Path) -> list[Image.Image]:
    image = Image.open(path)
    frames: list[Image.Image] = []
    try:
        while True:
            frames.append(image.convert("RGBA").copy())
            image.seek(image.tell() + 1)
    except EOFError:
        pass
    return frames


def _caption_card(text_lines: list[str], size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, "white")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(26, bold=True)
    body_font = _load_font(21)
    y_pos = 26
    for index, line in enumerate(text_lines):
        font = title_font if index == 0 else body_font
        draw.text((28, y_pos), line, fill="#0f172a", font=font)
        y_pos += 34 if index == 0 else 30
    return image


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    font_candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "DejaVuSans.ttf",
            "arial.ttf",
        ]
    )
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _slide_with_header(
    *,
    title: str,
    subtitle: str,
    image: Image.Image,
    canvas_size: tuple[int, int],
    crop_top_fraction: float = 0.0,
) -> Image.Image:
    slide = Image.new("RGBA", canvas_size, "white")
    draw = ImageDraw.Draw(slide)
    header_height = 150
    title_font = _load_font(34, bold=True)
    subtitle_font = _load_font(21)
    draw.rectangle((0, 0, canvas_size[0], header_height), fill="#f8fafc")
    draw.line((0, header_height, canvas_size[0], header_height), fill="#cbd5e1", width=2)
    draw.text((40, 24), title, fill="#0f172a", font=title_font)
    draw.text((40, 84), subtitle, fill="#334155", font=subtitle_font)

    prepared = image.convert("RGBA")
    if crop_top_fraction > 0.0:
        crop = int(prepared.height * crop_top_fraction)
        prepared = prepared.crop((0, crop, prepared.width, prepared.height))
    fitted = ImageOps.contain(prepared, (canvas_size[0] - 80, canvas_size[1] - header_height - 60))
    x_pos = (canvas_size[0] - fitted.width) // 2
    y_pos = header_height + (canvas_size[1] - header_height - fitted.height) // 2 + 12
    slide.alpha_composite(fitted, (x_pos, y_pos))
    return slide


def compose_campaign_recap_gif(
    output_path: Path,
    *,
    geometry_path: Path,
    comparison_paths: list[Path],
    surface_paths: list[Path],
    summary_lines: list[str],
) -> None:
    canvas_size = (1400, 900)
    frames: list[Image.Image] = []

    geometry_frame = _slide_with_header(
        title="Campaign replay: medium geometry",
        subtitle="Blue point: where the excitation starts. Red point: target site. The geometry is fixed; only the dynamical parameters change.",
        image=Image.open(geometry_path).convert("RGBA"),
        canvas_size=canvas_size,
        crop_top_fraction=0.10,
    )
    for _ in range(12):
        frames.append(geometry_frame.copy())

    comparison_sets = [_load_gif_frames(path) for path in comparison_paths]
    max_dynamic_frames = max(len(items) for items in comparison_sets)
    for frame_index in range(max_dynamic_frames):
        frame = Image.new("RGBA", canvas_size, "white")
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, canvas_size[0], 140), fill="#f8fafc")
        draw.line((0, 140, canvas_size[0], 140), fill="#cbd5e1", width=2)
        draw.text((40, 26), "Campaign replay: best versus worst cases", fill="#0f172a")
        draw.text(
            (40, 74),
            "Each panel compares two choices of parameters for the same medium. Read the green curve as useful arrival and the dashed curves as loss.",
            fill="#334155",
        )
        for panel_index, panel_frames in enumerate(comparison_sets):
            current = panel_frames[min(frame_index, len(panel_frames) - 1)]
            fitted = ImageOps.contain(current, (405, 500))
            x_pos = 40 + panel_index * 460
            y_pos = 170
            frame.alpha_composite(fitted, (x_pos, y_pos))
        caption = _caption_card(
            [
                "What to look for",
                "1. Does the excitation stay concentrated or does it dilute through the medium?",
                "2. Does the green target curve rise early or only very late?",
                "3. Does the bad case fail because it gets stuck or because it leaks away?",
            ],
            (1320, 120),
        )
        frame.alpha_composite(caption, (40, 760))
        frames.append(frame)

    for surface_path in surface_paths:
        surface_frame = _slide_with_header(
            title="Campaign replay: aggregate map",
            subtitle="The surface height is the measured quantity. Peaks mark parameter regions that work best for that medium.",
            image=Image.open(surface_path).convert("RGBA"),
            canvas_size=canvas_size,
            crop_top_fraction=0.02,
        )
        for _ in range(10):
            frames.append(surface_frame.copy())

    final_card = _caption_card(summary_lines, canvas_size)
    for _ in range(18):
        frames.append(final_card.copy())

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=110,
        loop=0,
        disposal=2,
    )


def visual_specs_to_payload(specs: dict[str, list[VisualCaseSpec]]) -> dict[str, object]:
    return {scenario_name: [asdict(case_spec) for case_spec in case_specs] for scenario_name, case_specs in specs.items()}
