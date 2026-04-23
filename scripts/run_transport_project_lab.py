from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
SOURCE_OUTPUT = ROOT / "outputs" / "transport_networks" / "dephasing_scan" / "latest"
LAB_OUTPUT = ROOT / "outputs" / "transport_networks" / "minimal_lab" / "latest"
BASELINE_SCRIPT = ROOT / "scripts" / "run_transport_dephasing_scan.py"


def _run_baseline() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, str(BASELINE_SCRIPT)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    LAB_OUTPUT.mkdir(parents=True, exist_ok=True)
    (LAB_OUTPUT / "baseline_run.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("transport baseline generation failed")


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _classify_best_regime(best_idx: int, n_points: int) -> str:
    if best_idx == 0:
        return "coherent"
    if best_idx == n_points - 1:
        return "strongly_dissipative"
    return "intermediate"


def main() -> int:
    _run_baseline()
    LAB_OUTPUT.mkdir(parents=True, exist_ok=True)

    results = _load_json(SOURCE_OUTPUT / "results.json")
    metrics = _load_json(SOURCE_OUTPUT / "metrics.json")
    config = _load_json(SOURCE_OUTPUT / "config_used.json")

    dephasing_rates = results["dephasing_rates_hz"]
    scenario_summaries: list[dict[str, object]] = []
    for scenario_block in results["scenarios"]:
        scenario = scenario_block["scenario"]
        name = scenario["name"]
        efficiencies = scenario_block["transport_efficiency"]
        coherences = scenario_block["mean_coherence_l1"]
        losses = scenario_block["final_loss_population"]
        best_idx = max(range(len(efficiencies)), key=lambda idx: efficiencies[idx])
        scenario_summaries.append(
            {
                "scenario": name,
                "topology": scenario["topology"],
                "n_sites": scenario["n_sites"],
                "main_observable": "sink_efficiency",
                "secondary_observables": ["population_dynamics", "coherence"],
                "best_regime": _classify_best_regime(best_idx, len(efficiencies)),
                "coherent": {
                    "dephasing_rate_hz": dephasing_rates[0],
                    "sink_efficiency": efficiencies[0],
                    "mean_coherence_l1": coherences[0],
                    "final_loss_population": losses[0],
                },
                "intermediate_best": {
                    "dephasing_rate_hz": dephasing_rates[best_idx],
                    "sink_efficiency": efficiencies[best_idx],
                    "mean_coherence_l1": coherences[best_idx],
                    "final_loss_population": losses[best_idx],
                },
                "strongly_dissipative": {
                    "dephasing_rate_hz": dephasing_rates[-1],
                    "sink_efficiency": efficiencies[-1],
                    "mean_coherence_l1": coherences[-1],
                    "final_loss_population": losses[-1],
                },
                "metrics_snapshot": metrics["scenarios"][name],
            }
        )

    summary = {
        "project_title": "Coherent and Dissipative Transport in Simple Open Quantum Networks",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "proposal_focus": {
            "main_observable": "sink_efficiency",
            "secondary_observables": ["population_dynamics", "coherence"],
            "optional_observables": ["purity", "entropy"],
            "core_graph_families": ["chain", "ring", "complete"],
            "core_regimes": ["coherent", "intermediate", "strongly_dissipative"],
        },
        "figures": {
            "main": "outputs/transport_networks/dephasing_scan/latest/figures/sink_efficiency_by_graph.png",
            "secondary_population": "outputs/transport_networks/dephasing_scan/latest/figures/population_dynamics_by_graph.png",
            "secondary_coherence": "outputs/transport_networks/dephasing_scan/latest/figures/coherence_by_graph.png",
        },
        "scenario_summaries": scenario_summaries,
        "input_files": {
            "results": "outputs/transport_networks/dephasing_scan/latest/results.json",
            "metrics": "outputs/transport_networks/dephasing_scan/latest/metrics.json",
            "config": "outputs/transport_networks/dephasing_scan/latest/config_used.json",
        },
    }

    (LAB_OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (LAB_OUTPUT / "config_used.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (LAB_OUTPUT / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
