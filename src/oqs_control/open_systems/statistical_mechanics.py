from __future__ import annotations

import numpy as np
from scipy.linalg import logm


def purity(rho: np.ndarray) -> float:
    return float(np.real_if_close(np.trace(rho @ rho)).real)


def von_neumann_entropy(rho: np.ndarray, base: float = np.e) -> float:
    evals = np.linalg.eigvalsh(0.5 * (rho + rho.conj().T)).real
    evals = np.clip(evals, 0.0, None)
    if evals.sum() == 0:
        return 0.0
    evals = evals / evals.sum()
    nz = evals > 0
    entropy = -np.sum(evals[nz] * np.log(evals[nz]))
    if base != np.e:
        entropy /= np.log(base)
    return float(entropy)


def relative_entropy(rho: np.ndarray, sigma: np.ndarray) -> float:
    rho_h = 0.5 * (rho + rho.conj().T)
    sigma_h = 0.5 * (sigma + sigma.conj().T)
    log_rho = logm(rho_h + 1e-12 * np.eye(rho_h.shape[0], dtype=complex))
    log_sigma = logm(sigma_h + 1e-12 * np.eye(sigma_h.shape[0], dtype=complex))
    value = np.trace(rho_h @ (log_rho - log_sigma))
    return float(np.real_if_close(value).real)


def free_energy_like(rho: np.ndarray, hamiltonian: np.ndarray, temperature: float) -> float:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    energy = np.trace(rho @ hamiltonian)
    entropy = von_neumann_entropy(rho)
    return float(np.real_if_close(energy).real - temperature * entropy)


def entropy_production_proxy(
    states: np.ndarray,
    steady_state: np.ndarray,
    times: np.ndarray,
) -> np.ndarray:
    rel = np.array([relative_entropy(rho, steady_state) for rho in states], dtype=float)
    return -np.gradient(rel, np.asarray(times, dtype=float))
