from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from .analysis import fft_spectrum, flatten_first_trace
from .config import NMRConfig
from .io import read_tnt
from .liouvillian import (
    NMRDissipationRates,
    OpenNMRSimulationResult,
    simulate_open_fid,
    simulate_open_reference_experiment,
)


@dataclass(frozen=True)
class SyntheticDissipativeFitResult:
    true_rates: NMRDissipationRates
    initial_rates: NMRDissipationRates
    fitted_rates: NMRDissipationRates
    success: bool
    message: str
    cost: float
    nfev: int
    relative_error_gamma_phi: float
    relative_error_gamma_relax: float
    target: OpenNMRSimulationResult
    fitted: OpenNMRSimulationResult


@dataclass(frozen=True)
class ReferenceDissipativeFitResult:
    reference_path: Path
    initial_rates: NMRDissipationRates
    fitted_rates: NMRDissipationRates
    success: bool
    message: str
    cost: float
    nfev: int
    n_points: int
    complex_scale: complex
    normalized_rmse_fid: float
    normalized_rmse_spectrum: float
    identifiability_warning: str
    reference_fid: np.ndarray
    reference_freq_hz: np.ndarray
    reference_spectrum: np.ndarray
    fitted: OpenNMRSimulationResult


@dataclass(frozen=True)
class SyntheticValidationCase:
    noise_std: float
    random_seed: int
    success: bool
    cost: float
    nfev: int
    fitted_rates: NMRDissipationRates
    relative_error_gamma_phi: float
    relative_error_gamma_relax: float


@dataclass(frozen=True)
class SyntheticValidationSuite:
    true_rates: NMRDissipationRates
    initial_rates: NMRDissipationRates
    n_points: int
    cases: tuple[SyntheticValidationCase, ...]
    success_count: int
    total_count: int
    max_relative_error_gamma_phi: float
    max_relative_error_gamma_relax: float
    median_relative_error_gamma_phi: float
    median_relative_error_gamma_relax: float


def _normalized_complex(signal: np.ndarray) -> np.ndarray:
    scale = np.max(np.abs(signal))
    if scale == 0:
        return np.array(signal, dtype=complex, copy=True)
    return np.asarray(signal, dtype=complex) / scale


def _rate_vector_to_rates(log_rates: np.ndarray) -> NMRDissipationRates:
    rates = np.exp(np.asarray(log_rates, dtype=float))
    return NMRDissipationRates(gamma_phi=float(rates[0]), gamma_relax=float(rates[1]))


def _rates_to_log_vector(rates: NMRDissipationRates) -> np.ndarray:
    return np.log(np.array([rates.gamma_phi, rates.gamma_relax], dtype=float))


def _best_complex_scale(model: np.ndarray, target: np.ndarray) -> complex:
    denom = np.vdot(model, model)
    if abs(denom) == 0:
        return 0.0 + 0.0j
    return complex(np.vdot(model, target) / denom)


def _normalized_rmse(model: np.ndarray, target: np.ndarray) -> float:
    denom = np.sqrt(np.mean(np.abs(target) ** 2))
    if denom == 0:
        return float(np.sqrt(np.mean(np.abs(model - target) ** 2)))
    return float(np.sqrt(np.mean(np.abs(model - target) ** 2)) / denom)


def run_synthetic_dissipative_recovery(
    config: NMRConfig | None = None,
    true_rates: NMRDissipationRates | None = None,
    initial_rates: NMRDissipationRates | None = None,
    n_points: int = 384,
    noise_std: float = 0.0,
    random_seed: int = 1234,
) -> SyntheticDissipativeFitResult:
    active_config = config or NMRConfig(n_acq=n_points, n_zf=n_points)
    target_rates = true_rates or NMRDissipationRates(gamma_phi=210.0, gamma_relax=55.0)
    guess_rates = initial_rates or NMRDissipationRates(gamma_phi=90.0, gamma_relax=18.0)

    target = simulate_open_reference_experiment(
        active_config,
        rates=target_rates,
        n_points=n_points,
    )
    target_fid = np.array(target.fid, copy=True)
    if noise_std > 0:
        rng = np.random.default_rng(random_seed)
        scale = np.max(np.abs(target_fid))
        noise = rng.normal(size=target_fid.size) + 1j * rng.normal(size=target_fid.size)
        target_fid = target_fid + noise_std * scale * noise / np.sqrt(2.0)

    target_norm = _normalized_complex(target_fid)

    def residual(log_rates: np.ndarray) -> np.ndarray:
        rates = _rate_vector_to_rates(log_rates)
        _, fid, _ = simulate_open_fid(
            active_config,
            rates=rates,
            n_points=n_points,
        )
        diff = _normalized_complex(fid) - target_norm
        return np.concatenate([diff.real, diff.imag])

    fit = least_squares(
        residual,
        _rates_to_log_vector(guess_rates),
        bounds=(np.log([1e-6, 1e-6]), np.log([1e5, 1e5])),
        xtol=1e-8,
        ftol=1e-8,
        gtol=1e-8,
        max_nfev=80,
    )
    fitted_rates = _rate_vector_to_rates(fit.x)
    fitted = simulate_open_reference_experiment(
        active_config,
        rates=fitted_rates,
        n_points=n_points,
    )
    # Keep the fitted result spectrum aligned with a noisy target if noise was used.
    if noise_std > 0:
        _, noisy_spectrum = fft_spectrum(target_fid, active_config.dwell_time)
        target = OpenNMRSimulationResult(
            time_s=target.time_s,
            fid=target_fid,
            spectrum=noisy_spectrum,
            freq_hz=target.freq_hz,
            states=target.states,
            checks=target.checks,
            purity=target.purity,
            entropy=target.entropy,
            relative_entropy_to_mixed=target.relative_entropy_to_mixed,
            entropy_production_proxy=target.entropy_production_proxy,
            free_energy_like=target.free_energy_like,
            rates=target.rates,
        )

    return SyntheticDissipativeFitResult(
        true_rates=target_rates,
        initial_rates=guess_rates,
        fitted_rates=fitted_rates,
        success=bool(fit.success),
        message=str(fit.message),
        cost=float(fit.cost),
        nfev=int(fit.nfev),
        relative_error_gamma_phi=float(
            abs(fitted_rates.gamma_phi - target_rates.gamma_phi) / target_rates.gamma_phi
        ),
        relative_error_gamma_relax=float(
            abs(fitted_rates.gamma_relax - target_rates.gamma_relax)
            / target_rates.gamma_relax
        ),
        target=target,
        fitted=fitted,
    )


def run_synthetic_validation_suite(
    config: NMRConfig | None = None,
    true_rates: NMRDissipationRates | None = None,
    initial_rates: NMRDissipationRates | None = None,
    n_points: int = 128,
    noise_levels: tuple[float, ...] = (0.0, 0.002, 0.01),
    random_seeds: tuple[int, ...] = (11, 23, 37),
) -> SyntheticValidationSuite:
    active_config = config or NMRConfig(n_acq=n_points, n_zf=n_points)
    target_rates = true_rates or NMRDissipationRates(gamma_phi=210.0, gamma_relax=55.0)
    guess_rates = initial_rates or NMRDissipationRates(gamma_phi=90.0, gamma_relax=18.0)
    cases: list[SyntheticValidationCase] = []

    for noise_std in noise_levels:
        for seed in random_seeds:
            result = run_synthetic_dissipative_recovery(
                config=active_config,
                true_rates=target_rates,
                initial_rates=guess_rates,
                n_points=n_points,
                noise_std=noise_std,
                random_seed=seed,
            )
            cases.append(
                SyntheticValidationCase(
                    noise_std=float(noise_std),
                    random_seed=int(seed),
                    success=result.success,
                    cost=result.cost,
                    nfev=result.nfev,
                    fitted_rates=result.fitted_rates,
                    relative_error_gamma_phi=result.relative_error_gamma_phi,
                    relative_error_gamma_relax=result.relative_error_gamma_relax,
                )
            )

    phi_errors = np.array([case.relative_error_gamma_phi for case in cases], dtype=float)
    relax_errors = np.array([case.relative_error_gamma_relax for case in cases], dtype=float)
    return SyntheticValidationSuite(
        true_rates=target_rates,
        initial_rates=guess_rates,
        n_points=n_points,
        cases=tuple(cases),
        success_count=sum(1 for case in cases if case.success),
        total_count=len(cases),
        max_relative_error_gamma_phi=float(np.max(phi_errors)),
        max_relative_error_gamma_relax=float(np.max(relax_errors)),
        median_relative_error_gamma_phi=float(np.median(phi_errors)),
        median_relative_error_gamma_relax=float(np.median(relax_errors)),
    )


def fit_reference_dissipative_rates(
    reference_path: str | Path,
    config: NMRConfig | None = None,
    initial_rates: NMRDissipationRates | None = None,
    n_points: int = 512,
) -> ReferenceDissipativeFitResult:
    """Diagnostic fit of effective dissipative rates to one real FID.

    This is intentionally conservative: only two effective rates are fitted and
    a complex scale absorbs receiver phase and amplitude. A single FID cannot
    identify a microscopic dissipative mechanism.
    """

    path = Path(reference_path)
    raw = flatten_first_trace(read_tnt(path))
    total_points = min(int(n_points), raw.size)
    active_config = config or NMRConfig(n_acq=total_points, n_zf=total_points)
    guess_rates = initial_rates or NMRDissipationRates(gamma_phi=160.0, gamma_relax=35.0)
    target = np.asarray(raw[:total_points], dtype=complex)
    target_norm = _normalized_complex(target)

    def residual(log_rates: np.ndarray) -> np.ndarray:
        rates = _rate_vector_to_rates(log_rates)
        _, fid, _ = simulate_open_fid(
            active_config,
            rates=rates,
            n_points=total_points,
        )
        model_norm = _normalized_complex(fid)
        scale = _best_complex_scale(model_norm, target_norm)
        diff = scale * model_norm - target_norm
        return np.concatenate([diff.real, diff.imag])

    fit = least_squares(
        residual,
        _rates_to_log_vector(guess_rates),
        bounds=(np.log([1e-6, 1e-6]), np.log([1e5, 1e5])),
        xtol=1e-8,
        ftol=1e-8,
        gtol=1e-8,
        max_nfev=80,
    )
    fitted_rates = _rate_vector_to_rates(fit.x)
    fitted = simulate_open_reference_experiment(
        active_config,
        rates=fitted_rates,
        n_points=total_points,
    )
    model_norm = _normalized_complex(fitted.fid)
    scale = _best_complex_scale(model_norm, target_norm)
    scaled_model = scale * model_norm
    ref_freq, ref_spec = fft_spectrum(target_norm, active_config.dwell_time)
    _, model_spec = fft_spectrum(scaled_model, active_config.dwell_time)

    return ReferenceDissipativeFitResult(
        reference_path=path,
        initial_rates=guess_rates,
        fitted_rates=fitted_rates,
        success=bool(fit.success),
        message=str(fit.message),
        cost=float(fit.cost),
        nfev=int(fit.nfev),
        n_points=total_points,
        complex_scale=scale,
        normalized_rmse_fid=_normalized_rmse(scaled_model, target_norm),
        normalized_rmse_spectrum=_normalized_rmse(model_spec, ref_spec),
        identifiability_warning=(
            "Diagnostic only: one FID with analytic complex scaling cannot identify "
            "a microscopic dissipative mechanism. Use T1/T2, offset sweeps, repeated "
            "runs, and tomography before making experimental-identification claims."
        ),
        reference_fid=target_norm,
        reference_freq_hz=ref_freq,
        reference_spectrum=ref_spec,
        fitted=fitted,
    )
