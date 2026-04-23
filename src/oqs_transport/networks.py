from __future__ import annotations

import numpy as np


def chain_adjacency(n_sites: int) -> np.ndarray:
    if n_sites < 2:
        raise ValueError("n_sites must be at least 2")
    adjacency = np.zeros((n_sites, n_sites), dtype=float)
    for site in range(n_sites - 1):
        adjacency[site, site + 1] = 1.0
        adjacency[site + 1, site] = 1.0
    return adjacency


def ring_adjacency(n_sites: int) -> np.ndarray:
    adjacency = chain_adjacency(n_sites)
    adjacency[0, -1] = 1.0
    adjacency[-1, 0] = 1.0
    return adjacency


def complete_adjacency(n_sites: int) -> np.ndarray:
    if n_sites < 2:
        raise ValueError("n_sites must be at least 2")
    adjacency = np.ones((n_sites, n_sites), dtype=float) - np.eye(n_sites, dtype=float)
    return adjacency


def static_disorder_energies(
    n_sites: int,
    disorder_strength: float,
    seed: int | None = None,
) -> np.ndarray:
    if disorder_strength < 0.0:
        raise ValueError("disorder_strength must be non-negative")
    rng = np.random.default_rng(seed)
    return rng.uniform(-disorder_strength, disorder_strength, size=int(n_sites))


def tight_binding_hamiltonian(
    adjacency: np.ndarray,
    coupling_hz: float,
    site_energies_hz: np.ndarray | None = None,
) -> np.ndarray:
    adjacency = np.asarray(adjacency, dtype=float)
    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        raise ValueError("adjacency must be a square matrix")
    n_sites = adjacency.shape[0]
    if not np.allclose(adjacency, adjacency.T):
        raise ValueError("adjacency must be symmetric")

    energies = np.zeros(n_sites, dtype=float)
    if site_energies_hz is not None:
        site_energies_hz = np.asarray(site_energies_hz, dtype=float)
        if site_energies_hz.shape != (n_sites,):
            raise ValueError("site_energies_hz must have shape (n_sites,)")
        energies = site_energies_hz

    hamiltonian = float(coupling_hz) * adjacency.astype(complex)
    hamiltonian += np.diag(energies.astype(complex))
    return hamiltonian
