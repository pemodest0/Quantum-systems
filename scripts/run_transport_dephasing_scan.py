from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
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

from oqs_transport import (  # noqa: E402
    chain_adjacency,
    complete_adjacency,
    enaqt_scan,
    ring_adjacency,
    static_disorder_energies,
)

OUTPUT_DIR = ROOT / "outputs" / "transport_networks" / "dephasing_scan" / "latest"
FIGURE_DIR = OUTPUT_DIR / "figures"


@dataclass(frozen=True)
class Scenario:
    name: str
    topology: str
    n_sites: int
    coupling_hz: float
    sink_rate_hz: float
    loss_rate_hz: float
    initial_site: int
    trap_site: int
    disorder_strength_hz: float
    seed: int


def _adjacency(topology: str, n_sites: int) -> np.ndarray:
    if topology == "chain":
        return chain_adjacency(n_sites)
    if topology == "ring":
        return ring_adjacency(n_sites)
    if topology == "complete":
        return complete_adjacency(n_sites)
    raise ValueError(f"unsupported topology: {topology}")


def _mkdirs() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_script_label() -> str:
    try:
        return str(Path(__file__).resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return "scripts/run_transport_dephasing_scan.py"


def main() -> int:
    _mkdirs()
    dephasing_rates = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4], dtype=float)
    times = np.linspace(0.0, 20.0, 900)

    scenarios = [
        Scenario(
            name="Destructive-interference network",
            topology="complete",
            n_sites=4,
            coupling_hz=1.0,
            sink_rate_hz=0.7,
            loss_rate_hz=0.02,
            initial_site=1,
            trap_site=0,
            disorder_strength_hz=0.0,
            seed=7,
        ),
        Scenario(
            name="Disordered ring",
            topology="ring",
            n_sites=4,
            coupling_hz=1.0,
            sink_rate_hz=0.6,
            loss_rate_hz=0.03,
            initial_site=2,
            trap_site=0,
            disorder_strength_hz=0.7,
            seed=11,
        ),
        Scenario(
            name="Ordered chain",
            topology="chain",
            n_sites=5,
            coupling_hz=1.0,
            sink_rate_hz=0.65,
            loss_rate_hz=0.02,
            initial_site=4,
            trap_site=0,
            disorder_strength_hz=0.0,
            seed=19,
        ),
    ]

    results_payload: dict[str, object] = {
        "dephasing_rates_hz": dephasing_rates.tolist(),
        "times": {"t_final": float(times[-1]), "n_samples": int(times.size)},
        "scenarios": [],
    }
    metrics_payload: dict[str, object] = {"scenarios": {}}

    fig_eff, ax_eff = plt.subplots(figsize=(8.4, 5.4))
    fig_coh, ax_coh = plt.subplots(figsize=(8.4, 5.4))
    fig_pop, axes_pop = plt.subplots(1, 3, figsize=(15.5, 4.3), sharey=True)

    for axis, scenario in zip(axes_pop, scenarios, strict=True):
        adjacency = _adjacency(scenario.topology, scenario.n_sites)
        site_energies = static_disorder_energies(
            scenario.n_sites,
            disorder_strength=scenario.disorder_strength_hz,
            seed=scenario.seed,
        )
        if scenario.disorder_strength_hz == 0.0:
            site_energies = np.zeros(scenario.n_sites, dtype=float)

        scan = enaqt_scan(
            adjacency=adjacency,
            coupling_hz=scenario.coupling_hz,
            dephasing_rates_hz=dephasing_rates,
            sink_rate_hz=scenario.sink_rate_hz,
            loss_rate_hz=scenario.loss_rate_hz,
            times=times,
            initial_site=scenario.initial_site,
            trap_site=scenario.trap_site,
            site_energies_hz=site_energies,
        )
        efficiencies = np.array([case.transport_efficiency for case in scan], dtype=float)
        coherences = np.array([case.mean_coherence_l1 for case in scan], dtype=float)
        losses = np.array([case.loss_population[-1] for case in scan], dtype=float)
        best_idx = int(np.argmax(efficiencies))
        best_case = scan[best_idx]

        ax_eff.plot(dephasing_rates, efficiencies, marker="o", lw=1.6, label=scenario.name)
        ax_coh.plot(dephasing_rates, coherences, marker="o", lw=1.6, label=scenario.name)

        for site in range(scenario.n_sites):
            axis.plot(
                best_case.times,
                np.real(best_case.states[:, site, site]),
                lw=1.3,
                label=fr"$P_{{{site}}}(t)$",
            )
        axis.plot(best_case.times, best_case.sink_population, lw=1.9, ls="--", color="black", label=r"$P_{\mathrm{sink}}(t)$")
        axis.set_title(scenario.name)
        axis.set_xlabel("Time (arb. units)")
        axis.grid(alpha=0.18)

        results_payload["scenarios"].append(
            {
                "scenario": asdict(scenario),
                "site_energies_hz": site_energies.tolist(),
                "transport_efficiency": efficiencies.tolist(),
                "final_loss_population": losses.tolist(),
                "mean_coherence_l1": coherences.tolist(),
                "best_dephasing_rate_hz": float(dephasing_rates[best_idx]),
                "best_efficiency": float(efficiencies[best_idx]),
            }
        )
        metrics_payload["scenarios"][scenario.name] = {
            "efficiency_no_dephasing": float(efficiencies[0]),
            "efficiency_optimal_dephasing": float(efficiencies[best_idx]),
            "efficiency_high_dephasing": float(efficiencies[-1]),
            "optimal_dephasing_rate_hz": float(dephasing_rates[best_idx]),
            "enaqt_gain_over_coherent": float(efficiencies[best_idx] - efficiencies[0]),
            "high_dephasing_penalty": float(efficiencies[best_idx] - efficiencies[-1]),
            "mean_coherence_at_optimum": float(coherences[best_idx]),
            "final_sink_population_at_optimum": float(best_case.sink_population[-1]),
            "final_loss_population_at_optimum": float(best_case.loss_population[-1]),
        }

    ax_eff.set_xlabel(r"Dephasing rate $\gamma_\phi$ (arb. units)")
    ax_eff.set_ylabel(r"Transport efficiency $\eta(T)$")
    ax_eff.set_title("Noise-assisted transport in small open quantum networks")
    ax_eff.grid(alpha=0.2)
    ax_eff.legend(frameon=False)
    fig_eff.tight_layout()

    ax_coh.set_xlabel(r"Dephasing rate $\gamma_\phi$ (arb. units)")
    ax_coh.set_ylabel(r"Mean coherence $C_{\ell_1}$")
    ax_coh.set_title("Coherence is reduced as transport is assisted or suppressed")
    ax_coh.grid(alpha=0.2)
    ax_coh.legend(frameon=False)
    fig_coh.tight_layout()

    axes_pop[0].set_ylabel("Population")
    axes_pop[0].legend(frameon=False, fontsize=8)
    fig_pop.suptitle("Population dynamics by graph at the representative dephasing regime", y=1.03)
    fig_pop.tight_layout()

    efficiency_path = FIGURE_DIR / "sink_efficiency_by_graph.png"
    coherence_path = FIGURE_DIR / "coherence_by_graph.png"
    population_path = FIGURE_DIR / "population_dynamics_by_graph.png"
    fig_eff.savefig(efficiency_path, dpi=220, bbox_inches="tight")
    fig_coh.savefig(coherence_path, dpi=220, bbox_inches="tight")
    fig_pop.savefig(population_path, dpi=220, bbox_inches="tight")
    # Backward-compatible filenames for older docs or scripts.
    fig_eff.savefig(FIGURE_DIR / "efficiency_vs_dephasing.png", dpi=220, bbox_inches="tight")
    fig_coh.savefig(FIGURE_DIR / "coherence_vs_dephasing.png", dpi=220, bbox_inches="tight")
    fig_pop.savefig(FIGURE_DIR / "sink_population_traces.png", dpi=220, bbox_inches="tight")
    plt.close(fig_eff)
    plt.close(fig_coh)
    plt.close(fig_pop)

    config_used = {
        "dephasing_rates_hz": dephasing_rates.tolist(),
        "times": times.tolist(),
        "scenarios": [asdict(scenario) for scenario in scenarios],
    }
    run_metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "script": _safe_script_label(),
        "output_dir": str(OUTPUT_DIR.relative_to(ROOT)),
    }

    (OUTPUT_DIR / "config_used.json").write_text(json.dumps(config_used, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "results.json").write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
