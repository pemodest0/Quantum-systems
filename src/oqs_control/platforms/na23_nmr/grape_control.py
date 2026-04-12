from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm, expm_frechet
from scipy.optimize import minimize

from .quadrupolar_qip import deviation_density, deviation_fidelity


@dataclass(frozen=True)
class ControlEnsembleMember:
    drift: np.ndarray
    rf_scale: float = 1.0
    weight: float = 1.0


@dataclass(frozen=True)
class GRAPEUnitaryResult:
    controls: np.ndarray
    dt_s: float
    initial_fidelity: float
    final_fidelity: float
    fidelity_history: tuple[float, ...]
    iterations: int
    success: bool
    message: str


@dataclass(frozen=True)
class GRAPEStatePreparationResult:
    controls: np.ndarray
    dt_s: float
    initial_deviation_fidelity: float
    final_deviation_fidelity: float
    initial_signal_efficiency: float
    final_signal_efficiency: float
    fidelity_history: tuple[float, ...]
    prepared_state: np.ndarray
    iterations: int
    success: bool
    message: str


def unitary_fidelity(target: np.ndarray, actual: np.ndarray) -> float:
    dim = target.shape[0]
    overlap = np.trace(target.conj().T @ actual)
    return float(np.clip(abs(overlap) ** 2 / dim**2, 0.0, 1.0))


def rectangular_controls(
    n_segments: int,
    duration_s: float,
    angle_rad: float,
    phase_rad: float = 0.0,
) -> np.ndarray:
    if n_segments <= 0:
        raise ValueError("n_segments must be positive")
    if duration_s <= 0.0:
        raise ValueError("duration_s must be positive")
    amplitude_rad_s = float(angle_rad) / (2.0 * float(duration_s))
    controls = np.zeros((int(n_segments), 2), dtype=float)
    controls[:, 0] = amplitude_rad_s * np.cos(float(phase_rad))
    controls[:, 1] = amplitude_rad_s * np.sin(float(phase_rad))
    return controls


def random_controls(
    n_segments: int,
    max_amplitude_rad_s: float,
    seed: int,
    scale: float = 0.35,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(
        scale=float(scale) * float(max_amplitude_rad_s),
        size=(int(n_segments), 2),
    )


def clip_controls(controls: np.ndarray, max_amplitude_rad_s: float) -> np.ndarray:
    max_amp = float(max_amplitude_rad_s)
    values = np.asarray(controls, dtype=float)
    amplitudes = np.linalg.norm(values, axis=1)
    scale = np.ones_like(amplitudes)
    mask = amplitudes > max_amp
    scale[mask] = max_amp / amplitudes[mask]
    return values * scale[:, None]


def propagate_controls(
    controls: np.ndarray,
    dt_s: float,
    drift: np.ndarray,
    control_x: np.ndarray,
    control_y: np.ndarray,
    rf_scale: float = 1.0,
) -> np.ndarray:
    total = np.eye(drift.shape[0], dtype=complex)
    for ux, uy in np.asarray(controls, dtype=float):
        hamiltonian = (
            np.asarray(drift, dtype=complex)
            + float(rf_scale) * (float(ux) * control_x + float(uy) * control_y)
        )
        total = expm(-1j * hamiltonian * float(dt_s)) @ total
    return total


def _segment_unitaries_and_derivatives(
    controls: np.ndarray,
    dt_s: float,
    drift: np.ndarray,
    control_x: np.ndarray,
    control_y: np.ndarray,
    rf_scale: float,
) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
    unitaries: list[np.ndarray] = []
    deriv_x: list[np.ndarray] = []
    deriv_y: list[np.ndarray] = []
    for ux, uy in np.asarray(controls, dtype=float):
        hamiltonian = (
            np.asarray(drift, dtype=complex)
            + float(rf_scale) * (float(ux) * control_x + float(uy) * control_y)
        )
        generator = -1j * hamiltonian * float(dt_s)
        unitary = expm(generator)
        dx = expm_frechet(
            generator,
            -1j * float(rf_scale) * control_x * float(dt_s),
            compute_expm=False,
        )
        dy = expm_frechet(
            generator,
            -1j * float(rf_scale) * control_y * float(dt_s),
            compute_expm=False,
        )
        unitaries.append(unitary)
        deriv_x.append(dx)
        deriv_y.append(dy)
    return unitaries, deriv_x, deriv_y


def _prefix_suffix(unitaries: list[np.ndarray]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    dim = unitaries[0].shape[0]
    n_segments = len(unitaries)
    prefix = [np.eye(dim, dtype=complex)]
    for unitary in unitaries:
        prefix.append(unitary @ prefix[-1])

    suffix = [np.eye(dim, dtype=complex) for _ in range(n_segments + 1)]
    for idx in range(n_segments - 1, -1, -1):
        suffix[idx] = suffix[idx + 1] @ unitaries[idx]
    return prefix, suffix


def unitary_fidelity_and_gradient(
    flat_controls: np.ndarray,
    target: np.ndarray,
    ensemble: tuple[ControlEnsembleMember, ...],
    control_x: np.ndarray,
    control_y: np.ndarray,
    dt_s: float,
) -> tuple[float, np.ndarray]:
    controls = np.asarray(flat_controls, dtype=float).reshape((-1, 2))
    dim = target.shape[0]
    total_weight = sum(float(member.weight) for member in ensemble)
    if total_weight <= 0.0:
        raise ValueError("ensemble weights must sum to a positive value")

    fidelity_acc = 0.0
    gradient_acc = np.zeros_like(controls)
    target_dag = target.conj().T

    for member in ensemble:
        unitaries, deriv_x, deriv_y = _segment_unitaries_and_derivatives(
            controls,
            dt_s,
            member.drift,
            control_x,
            control_y,
            member.rf_scale,
        )
        prefix, suffix = _prefix_suffix(unitaries)
        total_u = prefix[-1]
        overlap = np.trace(target_dag @ total_u)
        member_fidelity = abs(overlap) ** 2 / dim**2
        fidelity_acc += float(member.weight) * float(np.real(member_fidelity))

        for idx in range(controls.shape[0]):
            for col, derivative in enumerate((deriv_x[idx], deriv_y[idx])):
                d_total = suffix[idx + 1] @ derivative @ prefix[idx]
                d_overlap = np.trace(target_dag @ d_total)
                d_fidelity = 2.0 * np.real(np.conj(overlap) * d_overlap) / dim**2
                gradient_acc[idx, col] += float(member.weight) * float(d_fidelity)

    return fidelity_acc / total_weight, (gradient_acc / total_weight).reshape(-1)


def optimize_unitary_grape(
    target: np.ndarray,
    initial_controls: np.ndarray,
    dt_s: float,
    ensemble: tuple[ControlEnsembleMember, ...],
    control_x: np.ndarray,
    control_y: np.ndarray,
    max_amplitude_rad_s: float,
    max_iter: int = 80,
) -> GRAPEUnitaryResult:
    controls0 = clip_controls(initial_controls, max_amplitude_rad_s)
    bounds = [
        (-float(max_amplitude_rad_s), float(max_amplitude_rad_s))
        for _ in range(controls0.size)
    ]
    history: list[float] = []

    def objective(flat_controls: np.ndarray) -> tuple[float, np.ndarray]:
        fidelity, gradient = unitary_fidelity_and_gradient(
            flat_controls,
            target,
            ensemble,
            control_x,
            control_y,
            dt_s,
        )
        history.append(float(fidelity))
        return 1.0 - fidelity, -gradient

    initial_fidelity, _ = unitary_fidelity_and_gradient(
        controls0.reshape(-1),
        target,
        ensemble,
        control_x,
        control_y,
        dt_s,
    )
    result = minimize(
        objective,
        controls0.reshape(-1),
        jac=True,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": int(max_iter), "ftol": 1e-12, "gtol": 1e-8, "maxls": 30},
    )
    final_controls = clip_controls(result.x.reshape(controls0.shape), max_amplitude_rad_s)
    final_fidelity, _ = unitary_fidelity_and_gradient(
        final_controls.reshape(-1),
        target,
        ensemble,
        control_x,
        control_y,
        dt_s,
    )
    return GRAPEUnitaryResult(
        controls=final_controls,
        dt_s=float(dt_s),
        initial_fidelity=float(initial_fidelity),
        final_fidelity=float(final_fidelity),
        fidelity_history=tuple(history),
        iterations=int(result.nit),
        success=bool(result.success),
        message=str(result.message),
    )


def dephase_in_measurement_basis(rho: np.ndarray) -> np.ndarray:
    return np.diag(np.diag(np.asarray(rho, dtype=complex)))


def deviation_transfer_efficiency(prepared_state: np.ndarray, target_state: np.ndarray) -> float:
    prepared_dev = deviation_density(prepared_state)
    target_dev = deviation_density(target_state)
    norm_target_sq = float(np.real(np.trace(target_dev.conj().T @ target_dev)))
    if norm_target_sq <= 0.0:
        return 0.0
    overlap = float(np.real(np.trace(prepared_dev.conj().T @ target_dev)))
    return float(overlap / norm_target_sq)


def deviation_preparation_error(prepared_state: np.ndarray, target_state: np.ndarray) -> float:
    prepared_dev = deviation_density(prepared_state)
    target_dev = deviation_density(target_state)
    norm_target = float(np.linalg.norm(target_dev))
    if norm_target <= 0.0:
        return float(np.linalg.norm(prepared_dev))
    return float(np.linalg.norm(prepared_dev - target_dev) / norm_target)


def prepare_state_with_dephasing(
    controls: np.ndarray,
    dt_s: float,
    drift: np.ndarray,
    control_x: np.ndarray,
    control_y: np.ndarray,
    initial_state: np.ndarray,
    rf_scale: float = 1.0,
) -> np.ndarray:
    unitary = propagate_controls(controls, dt_s, drift, control_x, control_y, rf_scale=rf_scale)
    evolved = unitary @ initial_state @ unitary.conj().T
    prepared = dephase_in_measurement_basis(evolved)
    return prepared / np.trace(prepared)


def _state_preparation_fidelity(
    controls: np.ndarray,
    dt_s: float,
    drift: np.ndarray,
    control_x: np.ndarray,
    control_y: np.ndarray,
    initial_state: np.ndarray,
    target_state: np.ndarray,
) -> float:
    prepared = prepare_state_with_dephasing(
        controls,
        dt_s,
        drift,
        control_x,
        control_y,
        initial_state,
    )
    return 1.0 - deviation_preparation_error(prepared, target_state)


def optimize_state_preparation_grape(
    initial_state: np.ndarray,
    target_state: np.ndarray,
    initial_controls: np.ndarray,
    dt_s: float,
    drift: np.ndarray,
    control_x: np.ndarray,
    control_y: np.ndarray,
    max_amplitude_rad_s: float,
    max_iter: int = 120,
) -> GRAPEStatePreparationResult:
    """Optimize a dephase-after-control PPS benchmark by finite differences.

    The dimension is only four and this routine is used for paper reproduction,
    not real-time pulse design. The finite-difference gradient keeps the state
    preparation objective explicit and easy to audit.
    """

    controls0 = clip_controls(initial_controls, max_amplitude_rad_s)
    step = max(float(max_amplitude_rad_s) * 1e-5, 1e-3)
    bounds = [
        (-float(max_amplitude_rad_s), float(max_amplitude_rad_s))
        for _ in range(controls0.size)
    ]
    history: list[float] = []

    def fidelity_from_flat(flat_controls: np.ndarray) -> float:
        controls = flat_controls.reshape(controls0.shape)
        return _state_preparation_fidelity(
            controls,
            dt_s,
            drift,
            control_x,
            control_y,
            initial_state,
            target_state,
        )

    def objective(flat_controls: np.ndarray) -> tuple[float, np.ndarray]:
        base = fidelity_from_flat(flat_controls)
        history.append(float(base))
        gradient = np.zeros_like(flat_controls)
        for idx in range(flat_controls.size):
            plus = np.array(flat_controls, copy=True)
            minus = np.array(flat_controls, copy=True)
            plus[idx] += step
            minus[idx] -= step
            gradient[idx] = (fidelity_from_flat(plus) - fidelity_from_flat(minus)) / (2.0 * step)
        return 1.0 - base, -gradient

    initial_score = fidelity_from_flat(controls0.reshape(-1))
    initial_prepared = prepare_state_with_dephasing(
        controls0,
        dt_s,
        drift,
        control_x,
        control_y,
        initial_state,
    )
    result = minimize(
        objective,
        controls0.reshape(-1),
        jac=True,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": int(max_iter), "ftol": 1e-12, "gtol": 1e-8, "maxls": 25},
    )
    final_controls = clip_controls(result.x.reshape(controls0.shape), max_amplitude_rad_s)
    final_score = fidelity_from_flat(final_controls.reshape(-1))
    prepared_state = prepare_state_with_dephasing(
        final_controls,
        dt_s,
        drift,
        control_x,
        control_y,
        initial_state,
    )
    return GRAPEStatePreparationResult(
        controls=final_controls,
        dt_s=float(dt_s),
        initial_deviation_fidelity=deviation_fidelity(initial_prepared, target_state),
        final_deviation_fidelity=deviation_fidelity(prepared_state, target_state),
        initial_signal_efficiency=float(initial_score),
        final_signal_efficiency=float(final_score),
        fidelity_history=tuple(history),
        prepared_state=prepared_state,
        iterations=int(result.nit),
        success=bool(result.success),
        message=str(result.message),
    )


def thermal_deviation_state_from_iz(i_z: np.ndarray, scale: float = 0.08) -> np.ndarray:
    dim = i_z.shape[0]
    rho = np.eye(dim, dtype=complex) / dim + float(scale) * np.asarray(i_z, dtype=complex)
    rho = 0.5 * (rho + rho.conj().T)
    evals = np.linalg.eigvalsh(rho).real
    if np.min(evals) < -1e-12:
        raise ValueError("scale creates a non-positive density matrix")
    return rho / np.trace(rho)


def target_pseudo_pure_from_deviation(
    marked_index: int,
    initial_state: np.ndarray,
) -> np.ndarray:
    dev_initial = deviation_density(initial_state)
    target_dev = np.zeros_like(dev_initial)
    dim = initial_state.shape[0]
    diag_dev = np.real(np.diag(dev_initial))
    signal_scale = float((np.max(diag_dev) - np.min(diag_dev)) / 3.0)
    target_dev[int(marked_index), int(marked_index)] = 0.75 * signal_scale
    for idx in range(dim):
        if idx != int(marked_index):
            target_dev[idx, idx] = -0.25 * signal_scale
    target = np.eye(dim, dtype=complex) / dim + target_dev
    return target / np.trace(target)
