from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from oqs_control.platforms.na23_nmr.analysis import (
    apply_exponential_apodization,
)
from oqs_control.platforms.na23_nmr.config import NMRConfig
from oqs_control.platforms.na23_nmr.liouvillian import (
    NMRDissipationRates,
    simulate_open_reference_experiment,
)
from oqs_control.platforms.na23_nmr.operators import spin_operators
from oqs_control.platforms.na23_nmr.simulation import simulate_reference_experiment


def matrix_norm(value: np.ndarray) -> float:
    return float(np.linalg.norm(value))


def local_peak_frequency(freq_hz: np.ndarray, spectrum: np.ndarray, center_hz: float, window_hz: float) -> float:
    mask = np.abs(freq_hz - center_hz) <= window_hz
    if not np.any(mask):
        raise ValueError(f"No frequency bins in window around {center_hz} Hz")
    local_freq = freq_hz[mask]
    local_mag = np.abs(spectrum[mask])
    return float(local_freq[int(np.argmax(local_mag))])


def run_baseline(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ops = spin_operators(1.5)
    dim = ops.i_z.shape[0]
    identity = np.eye(dim, dtype=complex)
    config = NMRConfig(n_acq=2048, n_zf=2048)

    commutators = {
        "ix_iy_minus_i_iz": matrix_norm(ops.i_x @ ops.i_y - ops.i_y @ ops.i_x - 1j * ops.i_z),
        "iy_iz_minus_i_ix": matrix_norm(ops.i_y @ ops.i_z - ops.i_z @ ops.i_y - 1j * ops.i_x),
        "iz_ix_minus_i_iy": matrix_norm(ops.i_z @ ops.i_x - ops.i_x @ ops.i_z - 1j * ops.i_y),
    }
    hermiticity = {
        "ix": matrix_norm(ops.i_x - ops.i_x.conj().T),
        "iy": matrix_norm(ops.i_y - ops.i_y.conj().T),
        "iz": matrix_norm(ops.i_z - ops.i_z.conj().T),
        "i_plus_minus_i_minus_dagger": matrix_norm(ops.i_plus - ops.i_minus.conj().T),
    }
    traces = {
        "ix": float(abs(np.trace(ops.i_x))),
        "iy": float(abs(np.trace(ops.i_y))),
        "iz": float(abs(np.trace(ops.i_z))),
    }
    casimir_error = matrix_norm(ops.i_x @ ops.i_x + ops.i_y @ ops.i_y + ops.i_z @ ops.i_z - 1.5 * 2.5 * identity)
    iz_eigenvalues = sorted(float(v) for v in np.linalg.eigvalsh(ops.i_z).real)

    hamiltonian_hermiticity = {
        "h_q1": matrix_norm(config.h_q1 - config.h_q1.conj().T),
        "h_q2": matrix_norm(config.h_q2 - config.h_q2.conj().T),
        "h_bs": matrix_norm(config.h_bs - config.h_bs.conj().T),
        "h_rf": matrix_norm(config.h_rf - config.h_rf.conj().T),
        "h_offset": matrix_norm(config.h_offset - config.h_offset.conj().T),
        "h_free": matrix_norm(config.h_free - config.h_free.conj().T),
        "h_pulse": matrix_norm(config.h_pulse - config.h_pulse.conj().T),
    }

    closed = simulate_reference_experiment(config)
    peak_window = 900.0
    peaks = {
        "sat_minus_hz": local_peak_frequency(closed.freq_hz, closed.spectrum, -config.nu_q, peak_window),
        "central_hz": local_peak_frequency(closed.freq_hz, closed.spectrum, 0.0, peak_window),
        "sat_plus_hz": local_peak_frequency(closed.freq_hz, closed.spectrum, config.nu_q, peak_window),
    }
    peak_errors = {
        "sat_minus_hz": abs(peaks["sat_minus_hz"] + config.nu_q),
        "central_hz": abs(peaks["central_hz"]),
        "sat_plus_hz": abs(peaks["sat_plus_hz"] - config.nu_q),
    }

    shifted_config = NMRConfig(n_acq=2048, n_zf=2048, nu_q=12000.0)
    shifted = simulate_reference_experiment(shifted_config)
    shifted_sat_plus = local_peak_frequency(
        shifted.freq_hz,
        shifted.spectrum,
        shifted_config.nu_q,
        peak_window,
    )

    apodized = apply_exponential_apodization(closed.fid, config.dwell_time, line_broadening_hz=25.0)
    apodization_tail_ratio = float(abs(apodized[-1]) / max(abs(closed.fid[-1]), 1e-30))

    open_result = simulate_open_reference_experiment(
        NMRConfig(n_acq=256, n_zf=256),
        rates=NMRDissipationRates(gamma_phi=120.0, gamma_relax=25.0),
        n_points=256,
    )

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), constrained_layout=True)
    axes[0].bar(range(len(iz_eigenvalues)), iz_eigenvalues)
    axes[0].set_title("Spin-3/2 Iz eigenvalues")
    axes[0].set_xlabel("sorted eigenvalue index")
    axes[0].set_ylabel("m")
    axes[1].plot(closed.freq_hz, np.abs(closed.spectrum) / np.max(np.abs(closed.spectrum)), lw=1.2)
    axes[1].set_title("Internal reference spectrum baseline")
    axes[1].set_xlim(-30000, 30000)
    axes[1].set_xlabel("frequency (Hz)")
    axes[1].set_ylabel("normalized |FFT|")
    axes[1].grid(alpha=0.25)
    axes[2].plot(open_result.time_s * 1e3, open_result.purity, label="purity", lw=1.4)
    axes[2].plot(open_result.time_s * 1e3, open_result.entropy, label="entropy", lw=1.2)
    axes[2].set_title("Open-system physical diagnostics")
    axes[2].set_xlabel("time (ms)")
    axes[2].grid(alpha=0.25)
    axes[2].legend()
    figure_path = output_dir / "internal_validation_baseline.png"
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)

    tolerances = {
        "operator_algebra_abs": 1e-12,
        "hamiltonian_hermiticity_abs": 1e-12,
        "spectrum_peak_hz": 125.0,
        "open_trace_abs": 1e-10,
        "open_hermiticity_abs": 1e-10,
        "open_min_eigenvalue_floor": -1e-10,
    }
    passed = {
        "commutators": all(v < tolerances["operator_algebra_abs"] for v in commutators.values()),
        "operator_hermiticity": all(v < tolerances["operator_algebra_abs"] for v in hermiticity.values()),
        "operator_traces": all(v < tolerances["operator_algebra_abs"] for v in traces.values()),
        "casimir": casimir_error < tolerances["operator_algebra_abs"],
        "hamiltonians": all(v < tolerances["hamiltonian_hermiticity_abs"] for v in hamiltonian_hermiticity.values()),
        "spectrum_peaks": all(v < tolerances["spectrum_peak_hz"] for v in peak_errors.values()),
        "nu_q_dependence": abs(shifted_sat_plus - shifted_config.nu_q) < tolerances["spectrum_peak_hz"],
        "apodization": apodization_tail_ratio < 1.0,
        "open_trace": open_result.checks.max_trace_error < tolerances["open_trace_abs"],
        "open_hermiticity": open_result.checks.max_hermiticity_error < tolerances["open_hermiticity_abs"],
        "open_positivity": open_result.checks.min_eigenvalue > tolerances["open_min_eigenvalue_floor"],
    }
    results = {
        "status": "passed" if all(passed.values()) else "failed",
        "passed": passed,
        "tolerances": tolerances,
        "spin32": {
            "commutator_errors": commutators,
            "hermiticity_errors": hermiticity,
            "trace_abs": traces,
            "casimir_error": casimir_error,
            "iz_eigenvalues": iz_eigenvalues,
        },
        "hamiltonians": {
            "hermiticity_errors": hamiltonian_hermiticity,
            "nu_q_hz": config.nu_q,
            "delta_offset_hz": config.delta_offset_hz,
            "delta_bs_hz": config.delta_bs_hz,
        },
        "spectrum": {
            "peaks_hz": peaks,
            "peak_errors_hz": peak_errors,
            "shifted_nu_q_hz": shifted_config.nu_q,
            "shifted_sat_plus_hz": shifted_sat_plus,
            "apodization_tail_ratio": apodization_tail_ratio,
        },
        "open_system": {
            "checks": {
                "max_trace_error": open_result.checks.max_trace_error,
                "max_hermiticity_error": open_result.checks.max_hermiticity_error,
                "min_eigenvalue": open_result.checks.min_eigenvalue,
            },
            "final_purity": float(open_result.purity[-1]),
            "final_entropy": float(open_result.entropy[-1]),
        },
        "figures": [str(figure_path)],
    }
    (output_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run internal physics validation baseline.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = run_baseline(args.output_dir)
    print(json.dumps({"status": results["status"], "passed": results["passed"]}, indent=2))
    return 0 if results["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
