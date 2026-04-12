from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.open_systems.nonmarkovian import (
    damped_revival_coherence,
    fit_markovian_dephasing,
    markovian_dephasing_coherence,
    memory_witness,
    quasi_static_echo_coherence,
    quasi_static_ramsey_coherence,
    time_local_dephasing_rate,
)


PAPER_ID = "nonmarkov_noise_2022"
PAPER = {
    "paper_id": PAPER_ID,
    "title": "Characterization and control of non-Markovian quantum noise",
    "venue": "Nature Reviews Physics",
    "year": 2022,
    "doi": "10.1038/s42254-022-00446-2",
    "role": "scope_and_limits",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_ramsey_echo(
    path: Path,
    times_s: np.ndarray,
    markovian_true: np.ndarray,
    memory_ramsey: np.ndarray,
    memory_echo: np.ndarray,
    markov_fit: np.ndarray,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.2), constrained_layout=True)
    ax.plot(times_s * 1e3, markovian_true, label="Markovian semigroup Ramsey", lw=1.8)
    ax.plot(times_s * 1e3, memory_ramsey, label="memory Ramsey: quasi-static noise", lw=1.8)
    ax.plot(times_s * 1e3, markov_fit, "--", label="best Markovian fit to memory Ramsey", lw=1.3)
    ax.plot(times_s * 1e3, memory_echo, label="memory Hahn echo", lw=1.8)
    ax.set_title("Markovian dephasing vs memory revealed by echo control")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("coherence magnitude")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_trace_distance_revival(
    path: Path,
    times_s: np.ndarray,
    markovian_trace: np.ndarray,
    revival_trace: np.ndarray,
) -> None:
    increments = np.diff(revival_trace)
    positive = np.concatenate([[False], increments > 0.0])
    fig, ax = plt.subplots(figsize=(8.6, 5.0), constrained_layout=True)
    ax.plot(times_s * 1e3, markovian_trace, label="Markovian trace distance", lw=1.8)
    ax.plot(times_s * 1e3, revival_trace, label="memory trace distance with revivals", lw=1.8)
    ax.scatter(
        times_s[positive] * 1e3,
        revival_trace[positive],
        s=10,
        color="tab:red",
        label="information backflow increments",
    )
    ax.set_title("Trace-distance revival as a non-Markovianity witness")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("trace-distance proxy")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_time_local_rate(
    path: Path,
    times_s: np.ndarray,
    markovian_rate: np.ndarray,
    memory_rate: np.ndarray,
) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.0), constrained_layout=True)
    ax.plot(times_s * 1e3, markovian_rate, label="Markovian gamma_eff(t)", lw=1.8)
    ax.plot(times_s * 1e3, memory_rate, label="memory gamma_eff(t)", lw=1.2)
    ax.axhline(0.0, color="0.2", lw=0.9)
    ax.fill_between(
        times_s * 1e3,
        memory_rate,
        0.0,
        where=memory_rate < 0.0,
        color="tab:red",
        alpha=0.2,
        label="negative effective rate",
    )
    ax.set_title("Time-local dephasing rate: negative intervals indicate memory")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("gamma_eff(t) (s^-1)")
    ax.set_ylim(-4_000, 4_000)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_failure_signatures(path: Path, metrics: dict[str, float]) -> None:
    labels = [
        "BLP backflow",
        "negative-rate fraction",
        "max echo boost",
        "Markov fit RMSE",
    ]
    values = [
        metrics["blp_measure"],
        metrics["negative_rate_fraction"],
        metrics["max_echo_boost"],
        metrics["markovian_fit_rmse"],
    ]
    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    bars = ax.bar(labels, values, color=["#385f71", "#d46a6a", "#f2b84b", "#7b9e87"])
    ax.set_title("Operational failure signatures for a simple Lindblad model")
    ax.set_ylabel("dimensionless score")
    ax.grid(alpha=0.2, axis="y")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{value:.3g}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    times_s = np.linspace(0.0, 0.012, 700)
    markovian_gamma_s = 220.0
    quasi_static_sigma_rad_s = 360.0
    echo_refocusing_efficiency = 0.94
    revival_gamma_s = 80.0
    revival_omega_rad_s = 2.0 * np.pi * 380.0

    markovian_true = markovian_dephasing_coherence(times_s, markovian_gamma_s)
    memory_ramsey = quasi_static_ramsey_coherence(times_s, quasi_static_sigma_rad_s)
    memory_echo = quasi_static_echo_coherence(
        times_s,
        quasi_static_sigma_rad_s,
        refocusing_efficiency=echo_refocusing_efficiency,
    )
    markov_fit = fit_markovian_dephasing(times_s, memory_ramsey)
    revival_trace = damped_revival_coherence(times_s, revival_gamma_s, revival_omega_rad_s)
    markovian_trace = markovian_dephasing_coherence(times_s, revival_gamma_s)

    markov_rate = time_local_dephasing_rate(times_s, markovian_trace)
    memory_rate = time_local_dephasing_rate(times_s, revival_trace)
    witness = memory_witness(times_s, revival_trace, memory_echo, markov_fit.fitted)

    failure_metrics = {
        "blp_measure": witness.blp_measure,
        "negative_rate_fraction": witness.negative_rate_fraction,
        "min_time_local_rate_s^-1": witness.min_time_local_rate_s,
        "echo_boost_area_s": witness.echo_boost_area_s,
        "max_echo_boost": witness.max_echo_boost,
        "markovian_fit_gamma_s^-1": markov_fit.gamma_s,
        "markovian_fit_rmse": markov_fit.rmse,
        "final_memory_echo": float(memory_echo[-1]),
        "final_markovian_echo_prediction": float(markov_fit.fitted[-1]),
    }

    figures = {
        "markovian_vs_memory_ramsey_echo": figure_dir / "markovian_vs_memory_ramsey_echo.png",
        "trace_distance_revival": figure_dir / "trace_distance_revival.png",
        "time_local_rate_negative_intervals": figure_dir / "time_local_rate_negative_intervals.png",
        "lindblad_failure_signatures": figure_dir / "lindblad_failure_signatures.png",
    }
    plot_ramsey_echo(
        figures["markovian_vs_memory_ramsey_echo"],
        times_s,
        markovian_true,
        memory_ramsey,
        memory_echo,
        markov_fit.fitted,
    )
    plot_trace_distance_revival(
        figures["trace_distance_revival"],
        times_s,
        markovian_trace,
        revival_trace,
    )
    plot_time_local_rate(
        figures["time_local_rate_negative_intervals"],
        times_s,
        markov_rate,
        memory_rate,
    )
    plot_failure_signatures(figures["lindblad_failure_signatures"], failure_metrics)

    metrics = {
        "paper_id": PAPER_ID,
        "status": "completed",
        "benchmark_type": "operational Markovian-vs-memory effective benchmark",
        "failure_metrics": failure_metrics,
        "operational_definition": {
            "model_effective_sufficient": [
                "trace-distance proxy is monotonic within experimental tolerance",
                "time-local rates inferred from observables remain non-negative",
                "echo/control sequences do not outperform a Markovian fit beyond uncertainty",
                "one fitted semigroup rate predicts Ramsey and controlled sequences simultaneously",
            ],
            "failure_signatures": [
                "trace-distance revivals / positive BLP increments",
                "negative time-local dephasing rates",
                "Hahn echo or control recovery larger than Markovian prediction",
                "rate estimates depend strongly on the intervention sequence",
            ],
        },
        "nmr_project_relevance": {
            "use_simple_lindblad_when": [
                "single-FID fits are only used as diagnostic envelopes",
                "tomography trajectories show monotonic decay with stable fitted rates",
                "pulse interventions do not reveal recovery of lost coherence",
            ],
            "escalate_to_memory_model_when": [
                "QST shows coherence revivals",
                "echo/control sequences recover coherence beyond Lindblad predictions",
                "rates fitted from FID, spectrum, and QST disagree systematically",
                "state evolution after a pulse depends on earlier waiting/intervention history",
            ],
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    config_used = {
        "paper": PAPER,
        "implemented_equations": {
            "markovian_dephasing": "C_M(t) = exp(-gamma t)",
            "quasi_static_ramsey": "C_R(t) = exp[-0.5 sigma^2 t^2]",
            "quasi_static_echo": "C_E(t) = exp[-0.5 ((1-eff) sigma)^2 t^2]",
            "revival_trace_distance": "D(t) = |exp(-gamma t) cos(omega t)|",
            "blp_proxy": "N = sum_{Delta D > 0} Delta D",
            "time_local_rate": "gamma_eff(t) = -d log(D(t)) / dt",
        },
        "parameters": {
            "time_min_s": float(times_s[0]),
            "time_max_s": float(times_s[-1]),
            "time_points": int(times_s.size),
            "markovian_gamma_s^-1": markovian_gamma_s,
            "quasi_static_sigma_rad_s": quasi_static_sigma_rad_s,
            "echo_refocusing_efficiency": echo_refocusing_efficiency,
            "revival_gamma_s^-1": revival_gamma_s,
            "revival_omega_rad_s": revival_omega_rad_s,
        },
        "assumptions": [
            "The paper is a review/tools article; this is an operational benchmark, not a figure digitization.",
            "The memory model is deliberately minimal: correlated quasi-static dephasing and an explicit revival envelope.",
            "The benchmark defines when a simple Lindblad model is sufficient for this project and when it is not.",
        ],
    }

    results = {
        "paper_id": PAPER_ID,
        "metrics_file": str(output_dir / "metrics.json"),
        "config_file": str(output_dir / "config_used.json"),
        "markdown_note": str(output_dir / "reproduction_note.md"),
        "summary": {
            "blp_measure": witness.blp_measure,
            "negative_rate_fraction": witness.negative_rate_fraction,
            "max_echo_boost": witness.max_echo_boost,
            "markovian_fit_rmse": markov_fit.rmse,
        },
        "figures": {name: str(path) for name, path in figures.items()},
    }

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "config_used.json", config_used)
    write_json(output_dir / "results.json", results)
    (output_dir / "reproduction_note.md").write_text(
        "\n".join(
            [
                "# Characterization And Control Of Non-Markovian Quantum Noise",
                "",
                "This run implements an operational Markovian-vs-memory benchmark:",
                "a semigroup pure-dephasing model, a quasi-static memory model revealed",
                "by Hahn echo, and a trace-distance revival witness.",
                "",
                f"BLP backflow proxy: `{witness.blp_measure:.6g}`.",
                f"Negative-rate fraction: `{witness.negative_rate_fraction:.6g}`.",
                f"Max echo boost over Markovian prediction: `{witness.max_echo_boost:.6g}`.",
                f"Markovian fit RMSE to memory Ramsey: `{markov_fit.rmse:.6g}`.",
                "",
                "This is a scope-and-limits benchmark, not a full process-tensor",
                "tomography implementation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the non-Markovian noise Paper E target.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run(args.output_dir)
    print(json.dumps({"paper_id": PAPER_ID, "summary": results["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
