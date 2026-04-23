from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
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

from oqs_transport import adjacency_for_topology, classify_transport_regime, simulate_transport, static_disorder_energies  # noqa: E402

TOPOLOGIES = ("chain", "ring", "complete")
REGIME_CODE = {"coherent": 0, "intermediate": 1, "strongly_dissipative": 2}
REGIME_LABELS = ["coherent", "intermediate", "strongly dissipative"]


@dataclass(frozen=True)
class BaseParameters:
    n_sites: int
    coupling_hz: float
    sink_rate_hz: float
    loss_rate_hz: float
    disorder_strength_hz: float


def _load_config(path: Path) -> tuple[dict[str, object], BaseParameters, np.ndarray, np.ndarray, dict[str, np.ndarray], tuple[int, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    times = np.linspace(0.0, float(raw["time_grid"]["t_final"]), int(raw["time_grid"]["n_samples"]))
    rates = np.asarray(raw["dephasing_rates_hz"], dtype=float)
    base = raw["base_parameters"]
    base_parameters = BaseParameters(
        n_sites=int(base["n_sites"]),
        coupling_hz=float(base["coupling_hz"]),
        sink_rate_hz=float(base["sink_rate_hz"]),
        loss_rate_hz=float(base["loss_rate_hz"]),
        disorder_strength_hz=float(base["disorder_strength_hz"]),
    )
    sweeps = {key: np.asarray(values, dtype=float) for key, values in raw["sweeps"].items()}
    seeds = tuple(int(seed) for seed in raw["disorder_seeds"])
    return raw, base_parameters, times, rates, sweeps, seeds


def _initial_and_trap(topology: str, n_sites: int) -> tuple[int, int]:
    trap_site = 0
    if topology == "chain":
        return n_sites - 1, trap_site
    return n_sites // 2, trap_site


def _mean_std(values: list[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    if array.size == 1:
        return float(array[0]), 0.0
    return float(np.mean(array)), float(np.std(array, ddof=1))


def _run_case(
    topology: str,
    n_sites: int,
    coupling_hz: float,
    sink_rate_hz: float,
    loss_rate_hz: float,
    disorder_strength_hz: float,
    seeds: tuple[int, ...],
    times: np.ndarray,
    dephasing_rates: np.ndarray,
) -> dict[str, object]:
    adjacency = adjacency_for_topology(topology, n_sites)
    initial_site, trap_site = _initial_and_trap(topology, n_sites)
    active_seeds = seeds if disorder_strength_hz > 0.0 else (seeds[0],)

    efficiency_mean: list[float] = []
    efficiency_std: list[float] = []
    coherence_mean: list[float] = []
    coherence_std: list[float] = []
    loss_mean: list[float] = []
    loss_std: list[float] = []
    trace_diag: list[float] = []
    closure_diag: list[float] = []
    min_eig_diag: list[float] = []

    for rate in dephasing_rates:
        eta_values = []
        coh_values = []
        loss_values = []
        trace_values = []
        closure_values = []
        eig_values = []
        for seed in active_seeds:
            site_energies = (
                np.zeros(n_sites, dtype=float)
                if disorder_strength_hz == 0.0
                else static_disorder_energies(n_sites, disorder_strength_hz, seed)
            )
            result = simulate_transport(
                adjacency=adjacency,
                coupling_hz=coupling_hz,
                dephasing_rate_hz=float(rate),
                sink_rate_hz=sink_rate_hz,
                loss_rate_hz=loss_rate_hz,
                times=times,
                initial_site=initial_site,
                trap_site=trap_site,
                site_energies_hz=site_energies,
            )
            eta_values.append(result.transport_efficiency)
            coh_values.append(result.mean_coherence_l1)
            loss_values.append(float(result.loss_population[-1]))
            trace_values.append(result.max_trace_deviation)
            closure_values.append(result.max_population_closure_error)
            eig_values.append(result.min_state_eigenvalue)

        mean_eta, std_eta = _mean_std(eta_values)
        mean_coh, std_coh = _mean_std(coh_values)
        mean_loss, std_loss = _mean_std(loss_values)
        efficiency_mean.append(mean_eta)
        efficiency_std.append(std_eta)
        coherence_mean.append(mean_coh)
        coherence_std.append(std_coh)
        loss_mean.append(mean_loss)
        loss_std.append(std_loss)
        trace_diag.append(float(np.max(trace_values)))
        closure_diag.append(float(np.max(closure_values)))
        min_eig_diag.append(float(np.min(eig_values)))

    efficiency_curve = np.asarray(efficiency_mean, dtype=float)
    best_idx = int(np.argmax(efficiency_curve))
    best_regime = classify_transport_regime(best_idx, len(dephasing_rates))

    return {
        "topology": topology,
        "n_sites": n_sites,
        "coupling_hz": coupling_hz,
        "sink_rate_hz": sink_rate_hz,
        "loss_rate_hz": loss_rate_hz,
        "disorder_strength_hz": disorder_strength_hz,
        "initial_site": initial_site,
        "trap_site": trap_site,
        "n_realizations": len(active_seeds),
        "efficiency_mean": efficiency_mean,
        "efficiency_std": efficiency_std,
        "coherence_mean": coherence_mean,
        "coherence_std": coherence_std,
        "loss_mean": loss_mean,
        "loss_std": loss_std,
        "trace_diag": trace_diag,
        "closure_diag": closure_diag,
        "min_eig_diag": min_eig_diag,
        "best_idx": best_idx,
        "best_regime": best_regime,
        "best_rate_hz": float(dephasing_rates[best_idx]),
        "eta_best_mean": float(efficiency_mean[best_idx]),
        "eta_best_std": float(efficiency_std[best_idx]),
        "coherence_best_mean": float(coherence_mean[best_idx]),
        "loss_best_mean": float(loss_mean[best_idx]),
        "trace_diag_best": float(trace_diag[best_idx]),
        "closure_diag_best": float(closure_diag[best_idx]),
        "min_eig_best": float(min_eig_diag[best_idx]),
    }


def _plot_best_metric(path: Path, title: str, x_label: str, x_values: np.ndarray, results_by_topology: dict[str, list[dict[str, object]]], key_mean: str, key_std: str | None = None) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 5.6))
    for topology, case_results in results_by_topology.items():
        y = np.array([float(case[key_mean]) for case in case_results], dtype=float)
        ax.plot(x_values, y, marker="o", lw=1.8, label=topology)
        if key_std is not None:
            s = np.array([float(case[key_std]) for case in case_results], dtype=float)
            if np.any(s > 0.0):
                ax.fill_between(x_values, y - s, y + s, alpha=0.15)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_regime_map(path: Path, title: str, x_label: str, x_values: np.ndarray, results_by_topology: dict[str, list[dict[str, object]]]) -> None:
    matrix = np.array(
        [[REGIME_CODE[str(case["best_regime"])] for case in results_by_topology[topology]] for topology in TOPOLOGIES],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(8.8, 3.9))
    image = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0.0, vmax=2.0)
    ax.set_yticks(np.arange(len(TOPOLOGIES)), labels=list(TOPOLOGIES))
    ax.set_xticks(np.arange(len(x_values)), labels=[f"{value:.2f}" if float(value) != int(value) else str(int(value)) for value in x_values])
    ax.set_xlabel(x_label)
    ax.set_title(title)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, REGIME_LABELS[int(matrix[i, j])], ha="center", va="center", fontsize=8, color="white")
    fig.colorbar(image, ax=ax, ticks=[0, 1, 2], label="regime code")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _rows_for_sweep(sweep_name: str, parameter_value: float, result: dict[str, object]) -> dict[str, object]:
    return {
        "sweep": sweep_name,
        "topology": result["topology"],
        "parameter_value": parameter_value,
        "n_sites": result["n_sites"],
        "kappa_over_j": result["sink_rate_hz"] / result["coupling_hz"],
        "gamma_loss_over_j": result["loss_rate_hz"] / result["coupling_hz"],
        "w_over_j": result["disorder_strength_hz"] / result["coupling_hz"],
        "best_regime": result["best_regime"],
        "eta_best_mean": result["eta_best_mean"],
        "eta_best_std": result["eta_best_std"],
        "gamma_phi_best": result["best_rate_hz"],
        "coherence_best_mean": result["coherence_best_mean"],
        "loss_best_mean": result["loss_best_mean"],
        "trace_diag_best": result["trace_diag_best"],
        "closure_diag_best": result["closure_diag_best"],
        "min_eig_best": result["min_eig_best"],
        "n_realizations": result["n_realizations"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run systematic phase-slice sweeps for quantum transport.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "transport_phase_sweep_config.json"),
        help="Path to the phase-sweep configuration file.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    raw, base, times, dephasing_rates, sweeps, disorder_seeds = _load_config(config_path)
    output_dir = ROOT / "outputs" / "transport_networks" / str(raw["output_subdir"]) / "latest"
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, object]] = []
    results_payload: dict[str, object] = {"study_name": raw["study_name"], "sweeps": {}}

    sweep_definitions = {
        "n_sites": {
            "values": sweeps["n_sites"],
            "builder": lambda topology, value: dict(
                topology=topology,
                n_sites=int(value),
                coupling_hz=base.coupling_hz,
                sink_rate_hz=base.sink_rate_hz,
                loss_rate_hz=base.loss_rate_hz,
                disorder_strength_hz=base.disorder_strength_hz,
            ),
            "xlabel": r"Number of sites $N$",
            "title_key": "size",
        },
        "kappa_over_j": {
            "values": sweeps["kappa_over_j"],
            "builder": lambda topology, value: dict(
                topology=topology,
                n_sites=base.n_sites,
                coupling_hz=base.coupling_hz,
                sink_rate_hz=float(value) * base.coupling_hz,
                loss_rate_hz=base.loss_rate_hz,
                disorder_strength_hz=base.disorder_strength_hz,
            ),
            "xlabel": r"Sink ratio $\kappa/J$",
            "title_key": "kappa",
        },
        "Gamma_over_j": {
            "values": sweeps["Gamma_over_j"],
            "builder": lambda topology, value: dict(
                topology=topology,
                n_sites=base.n_sites,
                coupling_hz=base.coupling_hz,
                sink_rate_hz=base.sink_rate_hz,
                loss_rate_hz=float(value) * base.coupling_hz,
                disorder_strength_hz=base.disorder_strength_hz,
            ),
            "xlabel": r"Loss ratio $\Gamma/J$",
            "title_key": "loss",
        },
        "W_over_j": {
            "values": sweeps["W_over_j"],
            "builder": lambda topology, value: dict(
                topology=topology,
                n_sites=base.n_sites,
                coupling_hz=base.coupling_hz,
                sink_rate_hz=base.sink_rate_hz,
                loss_rate_hz=base.loss_rate_hz,
                disorder_strength_hz=float(value) * base.coupling_hz,
            ),
            "xlabel": r"Disorder ratio $W/J$",
            "title_key": "disorder",
        },
    }

    for sweep_name, definition in sweep_definitions.items():
        values = np.asarray(definition["values"], dtype=float)
        results_by_topology: dict[str, list[dict[str, object]]] = {topology: [] for topology in TOPOLOGIES}
        for topology in TOPOLOGIES:
            for value in values:
                params = definition["builder"](topology, value)
                result = _run_case(
                    topology=params["topology"],
                    n_sites=params["n_sites"],
                    coupling_hz=params["coupling_hz"],
                    sink_rate_hz=params["sink_rate_hz"],
                    loss_rate_hz=params["loss_rate_hz"],
                    disorder_strength_hz=params["disorder_strength_hz"],
                    seeds=disorder_seeds,
                    times=times,
                    dephasing_rates=dephasing_rates,
                )
                results_by_topology[topology].append(result)
                all_rows.append(_rows_for_sweep(sweep_name, float(value), result))

        _plot_best_metric(
            figure_dir / f"{definition['title_key']}_best_efficiency.png",
            f"{sweep_name}: best sink efficiency",
            definition["xlabel"],
            values,
            results_by_topology,
            "eta_best_mean",
            "eta_best_std",
        )
        _plot_best_metric(
            figure_dir / f"{definition['title_key']}_best_gamma_phi.png",
            f"{sweep_name}: optimal dephasing rate",
            definition["xlabel"],
            values,
            results_by_topology,
            "best_rate_hz",
            None,
        )
        _plot_best_metric(
            figure_dir / f"{definition['title_key']}_best_coherence.png",
            f"{sweep_name}: coherence at the optimum",
            definition["xlabel"],
            values,
            results_by_topology,
            "coherence_best_mean",
            None,
        )
        _plot_regime_map(
            figure_dir / f"{definition['title_key']}_regime_map.png",
            f"{sweep_name}: best-regime classification",
            definition["xlabel"],
            values,
            results_by_topology,
        )
        results_payload["sweeps"][sweep_name] = {
            "parameter_values": values.tolist(),
            "results_by_topology": {
                topology: case_results for topology, case_results in results_by_topology.items()
            },
        }

    with (output_dir / "phase_sweep_table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    (output_dir / "results.json").write_text(json.dumps(results_payload, indent=2), encoding="utf-8")
    (output_dir / "config_used.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "script": "scripts/run_transport_phase_sweep.py",
                "config_path": str(config_path),
                "dephasing_rates_hz": dephasing_rates.tolist(),
                "time_grid": {"t_final": float(times[-1]), "n_samples": int(times.size)},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
