from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import NMRConfig
from .simulation import biexponential_decay


TRANSITION_LABELS: tuple[str, str, str] = ("SAT-", "CT", "SAT+")


@dataclass(frozen=True)
class ReducedSpectralDensities:
    """Reduced spectral densities used by the minimal Na-23 relaxometry model."""

    j0_s: np.ndarray
    j1_s: np.ndarray
    j2_s: np.ndarray


@dataclass(frozen=True)
class QuadrupolarRelaxationParams:
    """Parameters for the Redfield-inspired effective quadrupolar model."""

    larmor_hz: float = 105.7507331e6
    quadrupolar_coupling_hz: float = 2_500.0
    asymmetry_eta: float = 0.0
    rate_scale: float = 1.0


@dataclass(frozen=True)
class RedfieldInspiredRates:
    """Effective rates in s^-1 derived from reduced spectral densities."""

    r1_slow: np.ndarray
    r1_fast: np.ndarray
    r2_central: np.ndarray
    r2_satellite: np.ndarray
    r2_fast: np.ndarray
    spectral_densities: ReducedSpectralDensities


@dataclass(frozen=True)
class RedfieldFitResult:
    """Grid-fit result mapping the current phenomenological envelope to the effective model."""

    tau_c_s: float
    quadrupolar_coupling_hz: float
    rmse: float
    rates: RedfieldInspiredRates


def _positive_array(values: np.ndarray | float, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if np.any(array <= 0.0):
        raise ValueError(f"{name} must be strictly positive")
    return array


def lorentzian_spectral_density(
    tau_c_s: np.ndarray | float,
    angular_frequency_rad_s: float,
) -> np.ndarray:
    """Return J(omega) = tau_c / (1 + omega^2 tau_c^2).

    This is the minimal single-correlation-time spectral density used to build a
    reduced Redfield-inspired benchmark. It is deliberately small and explicit:
    the paper reproduction should test model choices, not hide them.
    """

    tau = _positive_array(tau_c_s, "tau_c_s")
    omega = abs(float(angular_frequency_rad_s))
    return tau / (1.0 + (omega * tau) ** 2)


def reduced_spectral_densities(
    tau_c_s: np.ndarray | float,
    larmor_hz: float,
) -> ReducedSpectralDensities:
    omega0 = 2.0 * np.pi * float(larmor_hz)
    return ReducedSpectralDensities(
        j0_s=lorentzian_spectral_density(tau_c_s, 0.0),
        j1_s=lorentzian_spectral_density(tau_c_s, omega0),
        j2_s=lorentzian_spectral_density(tau_c_s, 2.0 * omega0),
    )


def redfield_inspired_rates(
    tau_c_s: np.ndarray | float,
    params: QuadrupolarRelaxationParams | None = None,
) -> RedfieldInspiredRates:
    """Build effective Na-23 quadrupolar rates from J0, J1, and J2.

    The rate combinations are a project-level closure inspired by Redfield
    quadrupolar relaxation: J1 and J2 drive longitudinal relaxation, while J0
    contributes strongly to transverse dephasing. This is not a claim that the
    review article's full derivation has been copied exactly.
    """

    active = params or QuadrupolarRelaxationParams()
    if active.quadrupolar_coupling_hz <= 0.0:
        raise ValueError("quadrupolar_coupling_hz must be positive")
    if active.rate_scale <= 0.0:
        raise ValueError("rate_scale must be positive")
    if active.asymmetry_eta < 0.0:
        raise ValueError("asymmetry_eta must be non-negative")

    densities = reduced_spectral_densities(tau_c_s, active.larmor_hz)
    coupling_rad_s = 2.0 * np.pi * active.quadrupolar_coupling_hz
    quadrupolar_prefactor = (
        active.rate_scale
        * coupling_rad_s**2
        * (1.0 + active.asymmetry_eta**2 / 3.0)
    )

    j0 = densities.j0_s
    j1 = densities.j1_s
    j2 = densities.j2_s

    r1_slow = quadrupolar_prefactor * (j1 + 4.0 * j2)
    r1_fast = quadrupolar_prefactor * (j0 + j1 + 4.0 * j2)
    r2_central = quadrupolar_prefactor * (3.0 * j0 + 0.5 * j1 + j2)
    r2_satellite = quadrupolar_prefactor * (3.0 * j0 + 1.5 * j1 + j2)
    r2_fast = quadrupolar_prefactor * (4.0 * j0 + 2.0 * j1 + 4.0 * j2)

    return RedfieldInspiredRates(
        r1_slow=np.asarray(r1_slow, dtype=float),
        r1_fast=np.asarray(r1_fast, dtype=float),
        r2_central=np.asarray(r2_central, dtype=float),
        r2_satellite=np.asarray(r2_satellite, dtype=float),
        r2_fast=np.asarray(r2_fast, dtype=float),
        spectral_densities=densities,
    )


def redfield_effective_envelopes(
    time_s: np.ndarray,
    rates: RedfieldInspiredRates,
) -> np.ndarray:
    """Return normalized SAT-, CT, SAT+ decay envelopes for a scalar rate set."""

    time = np.asarray(time_s, dtype=float)
    if time.ndim != 1:
        raise ValueError("time_s must be one-dimensional")
    if np.any(time < 0.0):
        raise ValueError("time_s must be non-negative")

    r2_central = float(np.asarray(rates.r2_central))
    r2_satellite = float(np.asarray(rates.r2_satellite))
    r2_fast = float(np.asarray(rates.r2_fast))

    ct = 0.7 * np.exp(-r2_central * time) + 0.3 * np.exp(-r2_fast * time)
    sat = 0.55 * np.exp(-r2_satellite * time) + 0.45 * np.exp(-r2_fast * time)
    return np.column_stack((sat, ct, sat))


def phenomenological_transition_envelopes(
    time_s: np.ndarray,
    decay_params: np.ndarray | None = None,
) -> np.ndarray:
    """Return normalized envelopes from the current MATLAB-derived biexponentials."""

    time = np.asarray(time_s, dtype=float)
    if time.ndim != 1:
        raise ValueError("time_s must be one-dimensional")
    active_params = np.asarray(
        NMRConfig().decay_params if decay_params is None else decay_params,
        dtype=float,
    )
    if active_params.shape != (3, 4):
        raise ValueError("decay_params must have shape (3, 4)")

    envelopes = np.zeros((time.size, 3), dtype=float)
    for idx in range(3):
        envelope = np.asarray(biexponential_decay(active_params[idx], time), dtype=float)
        normalizer = envelope[0] if abs(envelope[0]) > 1e-15 else 1.0
        envelopes[:, idx] = envelope / normalizer
    return envelopes


def apparent_initial_decay_rates(
    time_s: np.ndarray,
    envelopes: np.ndarray,
    fit_until_s: float,
) -> dict[str, float]:
    """Estimate single-exponential initial rates from log-envelope slopes."""

    time = np.asarray(time_s, dtype=float)
    values = np.asarray(envelopes, dtype=float)
    if values.shape != (time.size, 3):
        raise ValueError("envelopes must have shape (len(time_s), 3)")
    mask = (time > 0.0) & (time <= fit_until_s)
    if np.count_nonzero(mask) < 3:
        raise ValueError("fit window must contain at least three positive time points")

    rates: dict[str, float] = {}
    for idx, label in enumerate(TRANSITION_LABELS):
        clipped = np.clip(values[mask, idx], 1e-15, None)
        slope, _intercept = np.polyfit(time[mask], np.log(clipped), 1)
        rates[label] = float(max(0.0, -slope))
    return rates


def fit_redfield_effective_to_envelopes(
    time_s: np.ndarray,
    target_envelopes: np.ndarray,
    larmor_hz: float,
    tau_grid_s: np.ndarray,
    coupling_grid_hz: np.ndarray,
) -> RedfieldFitResult:
    """Fit the effective Redfield-inspired envelope to target transition envelopes."""

    time = np.asarray(time_s, dtype=float)
    target = np.asarray(target_envelopes, dtype=float)
    tau_grid = _positive_array(tau_grid_s, "tau_grid_s")
    coupling_grid = _positive_array(coupling_grid_hz, "coupling_grid_hz")

    if target.shape != (time.size, 3):
        raise ValueError("target_envelopes must have shape (len(time_s), 3)")

    best_rmse = np.inf
    best_tau = float(tau_grid[0])
    best_coupling = float(coupling_grid[0])
    best_rates: RedfieldInspiredRates | None = None

    for tau_c_s in tau_grid:
        for coupling_hz in coupling_grid:
            params = QuadrupolarRelaxationParams(
                larmor_hz=float(larmor_hz),
                quadrupolar_coupling_hz=float(coupling_hz),
            )
            rates = redfield_inspired_rates(float(tau_c_s), params)
            candidate = redfield_effective_envelopes(time, rates)
            rmse = float(np.sqrt(np.mean((candidate - target) ** 2)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_tau = float(tau_c_s)
                best_coupling = float(coupling_hz)
                best_rates = rates

    if best_rates is None:
        raise RuntimeError("empty fit grid")

    return RedfieldFitResult(
        tau_c_s=best_tau,
        quadrupolar_coupling_hz=best_coupling,
        rmse=best_rmse,
        rates=best_rates,
    )
