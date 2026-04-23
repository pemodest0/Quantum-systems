from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport import (  # noqa: E402
    build_visual_case_specs,
    compose_campaign_recap_gif,
    load_campaign_results,
    load_medium_campaign_config,
    render_case_comparison_gif,
    render_surface_figure,
    render_surface_rotation_gif,
    rerun_visual_case,
    visual_specs_to_payload,
)


def _safe_script_label() -> str:
    try:
        return str(Path(__file__).resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return "scripts/run_transport_visual_journey1.py"


def _dump_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _scenario_payload_map(results_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(payload["scenario_name"]): payload for payload in results_payload["scenarios"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Journey 1 visual artifacts for the medium campaign.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_medium_campaign_config.json"),
        help="Path to the medium campaign configuration file.",
    )
    parser.add_argument(
        "--results",
        default=str(ROOT / "outputs" / "transport_networks" / "medium_propagation" / "latest" / "results.json"),
        help="Path to the medium campaign results file.",
    )
    parser.add_argument(
        "--scenario-name",
        action="append",
        default=[],
        help="Restrict Journey 1 visuals to one or more exact scenario names. Can be passed multiple times.",
    )
    args = parser.parse_args(argv)

    config = load_medium_campaign_config(Path(args.config).resolve())
    results_payload = load_campaign_results(Path(args.results).resolve())
    scenario_payload_map = _scenario_payload_map(results_payload)

    output_dir = ROOT / "outputs" / "transport_networks" / config.output_subdir / "latest" / "visuals" / "journey1"
    animation_dir = output_dir / "animations"
    surface_dir = output_dir / "surfaces"
    recap_dir = output_dir / "recap"
    animation_dir.mkdir(parents=True, exist_ok=True)
    surface_dir.mkdir(parents=True, exist_ok=True)
    recap_dir.mkdir(parents=True, exist_ok=True)

    specs = build_visual_case_specs(config=config, results_payload=results_payload)
    scenario_filter = set(args.scenario_name)
    if scenario_filter:
        specs = {name: case_specs for name, case_specs in specs.items() if name in scenario_filter}
        results_payload = {
            **results_payload,
            "scenarios": [payload for payload in results_payload["scenarios"] if str(payload["scenario_name"]) in scenario_filter],
        }
        scenario_payload_map = _scenario_payload_map(results_payload)
    specs_payload = visual_specs_to_payload(specs)
    _dump_json(output_dir / "journey1_visual_payload.json", specs_payload)

    comparison_outputs: list[Path] = []
    summary_lines = [
        "Journey 1 recap",
        "What was built:",
        "- live 2D comparison animations",
        "- rotating 3D surfaces",
        "- a replay of the whole campaign",
        "",
        "What the baseline shows:",
        "- clean dynamics dominates most of the map",
        "- disorder reduces arrival at the target",
        "- the ring is the first place where weak phase scrambling starts to matter",
    ]

    for scenario_name, case_specs in specs.items():
        by_label = {case_spec.label: case_spec for case_spec in case_specs}
        best_case = by_label["best"]
        worst_case = by_label["worst"]
        best_result, best_coordinates, best_adjacency = rerun_visual_case(
            config=config,
            scenario_name=scenario_name,
            case_spec=best_case,
        )
        worst_result, worst_coordinates, worst_adjacency = rerun_visual_case(
            config=config,
            scenario_name=scenario_name,
            case_spec=worst_case,
        )
        scenario_slug = scenario_name.lower().replace(" ", "_")
        comparison_path = animation_dir / f"{scenario_slug}_best_vs_worst.gif"
        render_case_comparison_gif(
            comparison_path,
            scenario_name=scenario_name,
            best_case=best_case,
            worst_case=worst_case,
            best_result=best_result,
            best_coordinates=best_coordinates,
            best_adjacency=best_adjacency,
            worst_result=worst_result,
            worst_coordinates=worst_coordinates,
            worst_adjacency=worst_adjacency,
            initial_site=int(scenario_payload_map[scenario_name]["initial_site"]),
            trap_site=int(scenario_payload_map[scenario_name]["trap_site"]),
            stride=4,
            fps=10,
        )
        comparison_outputs.append(comparison_path)

    scenario_payloads = list(results_payload["scenarios"])
    surface_figure_specs = [
        ("efficiency_mean", "Transport success surfaces", "final target population", "transport_success_surfaces"),
        ("spreading_mean", "Spreading surfaces", "final mean squared displacement", "spreading_surfaces"),
        ("mixing_mean", "Mixing surfaces", "final graph-normalized entropy", "mixing_surfaces"),
    ]
    summary_surface_pngs: list[Path] = []
    for metric_key, title, z_label, slug in surface_figure_specs:
        png_path = surface_dir / f"{slug}.png"
        gif_path = surface_dir / f"{slug}_rotation.gif"
        render_surface_figure(
            png_path,
            scenario_payloads=scenario_payloads,
            metric_key=metric_key,
            title=title,
            z_label=z_label,
        )
        render_surface_rotation_gif(
            gif_path,
            scenario_payloads=scenario_payloads,
            metric_key=metric_key,
            title=title,
            z_label=z_label,
            frames=26,
        )
        if metric_key != "mixing_mean":
            summary_surface_pngs.append(png_path)

    compose_campaign_recap_gif(
        recap_dir / "campaign_recap.gif",
        geometry_path=ROOT / "outputs" / "transport_networks" / config.output_subdir / "latest" / "figures" / "medium_geometry_overview.png",
        comparison_paths=comparison_outputs,
        surface_paths=summary_surface_pngs,
        summary_lines=summary_lines,
    )

    run_metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "script": _safe_script_label(),
        "config_path": str(Path(args.config).resolve()),
        "results_path": str(Path(args.results).resolve()),
        "output_dir": str(output_dir.relative_to(ROOT)),
    }
    _dump_json(output_dir / "run_metadata.json", run_metadata)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
