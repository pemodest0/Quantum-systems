from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
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

from oqs_transport import generate_network_instance, graph_from_adjacency, simulate_transport, target_candidates  # noqa: E402


FAMILIES = ("sierpinski_gasket", "sierpinski_carpet_like", "square_lattice_2d")


def profile_config(profile: str) -> dict[str, object]:
    if profile == "smoke":
        return {"profile": "smoke", "n_sites_values": [8, 13], "t_final": 7.0, "n_time_samples": 56, "graph_seed_base": 10100}
    if profile == "interactive":
        return {"profile": "interactive", "n_sites_values": [8, 13, 20, 27], "t_final": 12.0, "n_time_samples": 120, "graph_seed_base": 10200}
    raise ValueError(f"unsupported profile: {profile}")


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _simulate_rows(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object], dict[str, float]]:
    rows: list[dict[str, object]] = []
    series: dict[str, object] = {}
    validation = {"max_trace_deviation": 0.0, "max_population_closure_error": 0.0, "min_state_eigenvalue": 1.0}
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    for family in FAMILIES:
        for n_sites in list(config["n_sites_values"]):
            seed = int(config["graph_seed_base"]) + int(n_sites) + len(rows)
            instance = generate_network_instance(family, n_sites=int(n_sites), seed=seed)
            initial_site = int(n_sites) - 1
            trap_site = int(target_candidates(instance, initial_site=initial_site)["far"])
            result = simulate_transport(
                adjacency=instance.adjacency,
                coupling_hz=1.0,
                dephasing_rate_hz=0.0,
                sink_rate_hz=0.65,
                loss_rate_hz=0.02,
                times=times,
                initial_site=initial_site,
                trap_site=trap_site,
                node_coordinates=instance.coordinates,
            )
            msd = np.asarray(result.mean_squared_displacement_t if result.mean_squared_displacement_t is not None else np.zeros_like(times), dtype=float)
            front = np.asarray(result.front_width_t if result.front_width_t is not None else np.zeros_like(times), dtype=float)
            positive = (times > times[1]) & (msd > 1e-10)
            exponent = float(np.polyfit(np.log(times[positive]), np.log(msd[positive]), deg=1)[0]) if np.count_nonzero(positive) >= 3 else 0.0
            graph = graph_from_adjacency(instance.adjacency)
            rows.append(
                {
                    "family": family,
                    "n_sites": int(n_sites),
                    "n_edges": graph.number_of_edges(),
                    "density": float(nx.density(graph)),
                    "arrival": float(result.transport_efficiency),
                    "final_msd": float(msd[-1]),
                    "final_front_width": float(front[-1]),
                    "participation_ratio": float(result.final_participation_ratio),
                    "ipr": float(result.final_ipr),
                    "msd_exponent": exponent,
                    "max_trace_deviation": float(result.max_trace_deviation),
                    "max_population_closure_error": float(result.max_population_closure_error),
                    "min_state_eigenvalue": float(result.min_state_eigenvalue),
                }
            )
            series[f"{family}_N{n_sites}"] = {
                "family": family,
                "n_sites": int(n_sites),
                "coordinates": instance.coordinates.tolist(),
                "adjacency": instance.adjacency.tolist(),
                "times": times.tolist(),
                "msd": msd.tolist(),
                "front_width": front.tolist(),
            }
            validation["max_trace_deviation"] = max(validation["max_trace_deviation"], float(result.max_trace_deviation))
            validation["max_population_closure_error"] = max(validation["max_population_closure_error"], float(result.max_population_closure_error))
            validation["min_state_eigenvalue"] = min(validation["min_state_eigenvalue"], float(result.min_state_eigenvalue))
    return rows, series, validation


def _fractal_verdict(rows: list[dict[str, object]]) -> dict[str, object]:
    sizes = sorted({int(row["n_sites"]) for row in rows})
    changed = 0
    comparisons = []
    for n_sites in sizes:
        lattice = [row for row in rows if row["family"] == "square_lattice_2d" and int(row["n_sites"]) == n_sites]
        if not lattice:
            continue
        lattice_msd = float(lattice[0]["final_msd"])
        for family in ("sierpinski_gasket", "sierpinski_carpet_like"):
            item = [row for row in rows if row["family"] == family and int(row["n_sites"]) == n_sites]
            if not item:
                continue
            ratio = float(item[0]["final_msd"]) / max(lattice_msd, 1e-12)
            comparisons.append({"family": family, "n_sites": n_sites, "msd_ratio_vs_lattice": ratio})
            if ratio < 0.5:
                changed += 1
    return {"comparisons": comparisons, "fractal_geometry_changes_spreading": bool(changed >= 2), "changed_count": changed}


def _plot_msd(series: dict[str, object], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    for key, payload in series.items():
        if int(payload["n_sites"]) != max(int(item["n_sites"]) for item in series.values()):
            continue
        ax.plot(payload["times"], payload["msd"], label=payload["family"], linewidth=2)
    ax.set_title("Fractal versus lattice spreading")
    ax.set_xlabel("time")
    ax.set_ylabel("mean squared displacement")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_geometry(series: dict[str, object], path: Path) -> None:
    selected = [payload for payload in series.values() if int(payload["n_sites"]) == max(int(item["n_sites"]) for item in series.values())]
    fig, axes = plt.subplots(1, len(selected), figsize=(4.0 * len(selected), 4.0), constrained_layout=True)
    if len(selected) == 1:
        axes = [axes]
    for ax, payload in zip(axes, selected, strict=False):
        coords = np.asarray(payload["coordinates"], dtype=float)
        graph = nx.from_numpy_array(np.asarray(payload["adjacency"], dtype=float))
        positions = {index: tuple(coords[index]) for index in range(coords.shape[0])}
        nx.draw_networkx_edges(graph, positions, ax=ax, width=1.0, edge_color="#607d8b")
        nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=50, node_color="#ffca28", edgecolors="black", linewidths=0.3)
        ax.set_title(str(payload["family"]))
        ax.axis("equal")
        ax.axis("off")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _write_summary(output_dir: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Fractal Geometry Follow-Up",
        "",
        f"- Fractal spreading verdict: `{metrics.get('fractal_geometry_changes_spreading', False)}`.",
        f"- Changed comparisons: `{metrics.get('changed_count', 0)}`.",
        f"- Numerics pass: `{metrics.get('numerics_pass', False)}`.",
        "",
        "The claim is accepted only if fractal MSD/front width differ from the 2D lattice in at least two size comparisons.",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_campaign(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    rows, series, validation = _simulate_rows(config)
    verdict = _fractal_verdict(rows)
    numerics_pass = bool(validation["max_trace_deviation"] < 1e-8 and validation["max_population_closure_error"] < 1e-8 and validation["min_state_eigenvalue"] > -1e-7)
    metrics = {"profile": config["profile"], "row_count": len(rows), "validation": validation, "numerics_pass": numerics_pass, **verdict}
    _write_csv(rows, output_dir / "fractal_scaling_summary.csv")
    (output_dir / "fractal_series.json").write_text(json.dumps(series, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat()}, indent=2, ensure_ascii=False), encoding="utf-8")
    _plot_msd(series, figures_dir / "fractal_vs_lattice_msd.png")
    _plot_geometry(series, figures_dir / "fractal_geometry_panel.png")
    _write_summary(output_dir, metrics)
    return metrics


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run fractal geometry follow-up for open quantum transport.")
    parser.add_argument("--profile", choices=["smoke", "interactive"], default="smoke")
    parser.add_argument("--output-subdir", default="fractal_geometry_followup")
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
