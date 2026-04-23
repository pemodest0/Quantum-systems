from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .networks import static_disorder_energies

SUPPORTED_MEDIUM_TYPES = (
    "chain_1d",
    "ring",
    "square_lattice_2d",
    "bottleneck_lattice",
    "clustered_lattice",
)

SUPPORTED_COUPLING_LAWS = (
    "nearest_neighbor",
    "exponential_decay",
    "power_law",
)

SUPPORTED_SITE_ENERGY_PROFILES = (
    "uniform",
    "static_disorder",
    "gradient_x",
    "gradient_x_plus_disorder",
)


@dataclass(frozen=True)
class MediumDefinition:
    medium_type: str
    adjacency: np.ndarray
    coordinates: np.ndarray
    site_energies_hz: np.ndarray
    labels: tuple[str, ...]
    metadata: dict[str, float | int | str]


def _validate_medium_type(medium_type: str) -> None:
    if medium_type not in SUPPORTED_MEDIUM_TYPES:
        raise ValueError(f"unsupported medium_type: {medium_type}")


def _validate_coupling_law(coupling_law: str) -> None:
    if coupling_law not in SUPPORTED_COUPLING_LAWS:
        raise ValueError(f"unsupported coupling_law: {coupling_law}")


def _validate_site_profile(site_energy_profile: str) -> None:
    if site_energy_profile not in SUPPORTED_SITE_ENERGY_PROFILES:
        raise ValueError(f"unsupported site_energy_profile: {site_energy_profile}")


def chain_coordinates(n_sites: int, length_scale: float = 1.0) -> np.ndarray:
    if n_sites < 2:
        raise ValueError("n_sites must be at least 2")
    if length_scale <= 0.0:
        raise ValueError("length_scale must be positive")
    x = np.arange(n_sites, dtype=float) * float(length_scale)
    return np.column_stack([x, np.zeros(n_sites, dtype=float)])


def ring_coordinates(n_sites: int, length_scale: float = 1.0) -> np.ndarray:
    if n_sites < 3:
        raise ValueError("ring requires at least 3 sites")
    if length_scale <= 0.0:
        raise ValueError("length_scale must be positive")
    radius = float(length_scale) / (2.0 * np.sin(np.pi / n_sites))
    angles = np.linspace(np.pi / 2.0, np.pi / 2.0 - 2.0 * np.pi, n_sites, endpoint=False)
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])


def square_lattice_coordinates(n_rows: int, n_cols: int, length_scale: float = 1.0) -> np.ndarray:
    if n_rows < 2 or n_cols < 2:
        raise ValueError("square lattice requires at least 2 rows and 2 cols")
    if length_scale <= 0.0:
        raise ValueError("length_scale must be positive")
    coords: list[list[float]] = []
    for row in range(n_rows):
        for col in range(n_cols):
            coords.append([float(col) * length_scale, -float(row) * length_scale])
    return np.asarray(coords, dtype=float)


def bottleneck_lattice_coordinates(
    n_rows: int,
    n_cols_left: int,
    n_cols_right: int,
    length_scale: float = 1.0,
    gap_scale: float = 1.8,
) -> np.ndarray:
    if min(n_rows, n_cols_left, n_cols_right) < 1:
        raise ValueError("bottleneck lattice dimensions must be positive")
    if length_scale <= 0.0 or gap_scale <= 0.0:
        raise ValueError("length and gap scales must be positive")
    coords: list[list[float]] = []
    for row in range(n_rows):
        for col in range(n_cols_left):
            coords.append([float(col) * length_scale, -float(row) * length_scale])
    x_offset = (n_cols_left - 1) * length_scale + gap_scale * length_scale
    for row in range(n_rows):
        for col in range(n_cols_right):
            coords.append([x_offset + float(col) * length_scale, -float(row) * length_scale])
    return np.asarray(coords, dtype=float)


def clustered_lattice_coordinates(
    cluster_size: int,
    length_scale: float = 1.0,
    cluster_spacing: float = 3.0,
) -> np.ndarray:
    if cluster_size < 2:
        raise ValueError("cluster_size must be at least 2")
    if length_scale <= 0.0 or cluster_spacing <= 0.0:
        raise ValueError("length and spacing must be positive")
    left = square_lattice_coordinates(2, cluster_size, length_scale=length_scale)
    right = square_lattice_coordinates(2, cluster_size, length_scale=length_scale)
    right[:, 0] += (cluster_size - 1) * length_scale + cluster_spacing * length_scale
    return np.vstack([left, right])


def build_medium_coordinates(
    *,
    medium_type: str,
    n_sites: int | None = None,
    n_rows: int | None = None,
    n_cols: int | None = None,
    n_cols_left: int | None = None,
    n_cols_right: int | None = None,
    cluster_size: int | None = None,
    length_scale: float = 1.0,
) -> np.ndarray:
    _validate_medium_type(medium_type)
    if medium_type == "chain_1d":
        if n_sites is None:
            raise ValueError("chain_1d requires n_sites")
        return chain_coordinates(n_sites, length_scale=length_scale)
    if medium_type == "ring":
        if n_sites is None:
            raise ValueError("ring requires n_sites")
        return ring_coordinates(n_sites, length_scale=length_scale)
    if medium_type == "square_lattice_2d":
        if n_rows is None or n_cols is None:
            raise ValueError("square_lattice_2d requires n_rows and n_cols")
        return square_lattice_coordinates(n_rows, n_cols, length_scale=length_scale)
    if medium_type == "bottleneck_lattice":
        if n_rows is None or n_cols_left is None or n_cols_right is None:
            raise ValueError("bottleneck_lattice requires n_rows, n_cols_left, and n_cols_right")
        return bottleneck_lattice_coordinates(
            n_rows=n_rows,
            n_cols_left=n_cols_left,
            n_cols_right=n_cols_right,
            length_scale=length_scale,
        )
    if medium_type == "clustered_lattice":
        if cluster_size is None:
            raise ValueError("clustered_lattice requires cluster_size")
        return clustered_lattice_coordinates(cluster_size=cluster_size, length_scale=length_scale)
    raise ValueError(f"unsupported medium_type: {medium_type}")


def _distance_matrix(coordinates: np.ndarray) -> np.ndarray:
    diffs = coordinates[:, None, :] - coordinates[None, :, :]
    return np.linalg.norm(diffs, axis=2)


def _nearest_neighbor_pairs(medium_type: str, coordinates: np.ndarray, length_scale: float) -> np.ndarray:
    distances = _distance_matrix(coordinates)
    adjacency = np.zeros((coordinates.shape[0], coordinates.shape[0]), dtype=float)
    if medium_type == "ring":
        mask = (distances > 1e-12) & np.isclose(distances, length_scale, atol=1e-8)
    elif medium_type == "clustered_lattice":
        cutoff = 1.05 * float(length_scale)
        mask = (distances > 1e-12) & (distances <= cutoff)
        # Add one bridge between the two clusters.
        n_half = coordinates.shape[0] // 2
        left_bridge = n_half - 1
        right_bridge = n_half
        mask[left_bridge, right_bridge] = True
        mask[right_bridge, left_bridge] = True
    elif medium_type == "bottleneck_lattice":
        cutoff = 1.05 * float(length_scale)
        mask = (distances > 1e-12) & (distances <= cutoff)
        left_cluster_size = int(np.sum(coordinates[:, 0] < np.mean(coordinates[:, 0])))
        n_rows = int(np.unique(coordinates[:left_cluster_size, 1]).size)
        left_bridge = left_cluster_size - n_rows // 2 - 1
        right_bridge = left_cluster_size + n_rows // 2
        mask[left_bridge, right_bridge] = True
        mask[right_bridge, left_bridge] = True
    else:
        cutoff = 1.05 * float(length_scale)
        mask = (distances > 1e-12) & (distances <= cutoff)
    adjacency[mask] = 1.0
    adjacency = np.maximum(adjacency, adjacency.T)
    np.fill_diagonal(adjacency, 0.0)
    return adjacency


def build_coupling_adjacency(
    coordinates: np.ndarray,
    *,
    medium_type: str,
    coupling_law: str,
    length_scale: float,
    decay_length: float = 1.5,
    power_law_exponent: float = 3.0,
    cutoff_radius: float | None = None,
) -> np.ndarray:
    _validate_coupling_law(coupling_law)
    coordinates = np.asarray(coordinates, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[0] < 2:
        raise ValueError("coordinates must be a 2D array with at least two sites")

    if coupling_law == "nearest_neighbor":
        return _nearest_neighbor_pairs(medium_type, coordinates, length_scale=float(length_scale))

    distances = _distance_matrix(coordinates)
    adjacency = np.zeros_like(distances)
    valid = distances > 1e-12
    if cutoff_radius is not None:
        valid &= distances <= float(cutoff_radius)

    if coupling_law == "exponential_decay":
        if decay_length <= 0.0:
            raise ValueError("decay_length must be positive")
        adjacency[valid] = np.exp(-(distances[valid] / float(decay_length)))
    elif coupling_law == "power_law":
        if power_law_exponent <= 0.0:
            raise ValueError("power_law_exponent must be positive")
        adjacency[valid] = (float(length_scale) / distances[valid]) ** float(power_law_exponent)
    else:
        raise ValueError(f"unsupported coupling_law: {coupling_law}")

    adjacency = 0.5 * (adjacency + adjacency.T)
    np.fill_diagonal(adjacency, 0.0)
    return adjacency


def build_site_energies(
    coordinates: np.ndarray,
    *,
    site_energy_profile: str,
    disorder_strength_hz: float,
    seed: int | None = None,
    gradient_strength_hz: float = 0.0,
) -> np.ndarray:
    _validate_site_profile(site_energy_profile)
    coordinates = np.asarray(coordinates, dtype=float)
    n_sites = int(coordinates.shape[0])
    if disorder_strength_hz < 0.0:
        raise ValueError("disorder_strength_hz must be non-negative")

    if site_energy_profile == "uniform":
        return np.zeros(n_sites, dtype=float)

    if site_energy_profile == "static_disorder":
        return static_disorder_energies(n_sites, disorder_strength_hz, seed=seed)

    x_coords = coordinates[:, 0]
    x_centered = x_coords - np.mean(x_coords)
    gradient = float(gradient_strength_hz) * x_centered

    if site_energy_profile == "gradient_x":
        return gradient.astype(float)

    if site_energy_profile == "gradient_x_plus_disorder":
        return gradient.astype(float) + static_disorder_energies(n_sites, disorder_strength_hz, seed=seed)

    raise ValueError(f"unsupported site_energy_profile: {site_energy_profile}")


def medium_labels(medium_type: str, n_sites: int) -> tuple[str, ...]:
    prefix = {
        "chain_1d": "chain",
        "ring": "ring",
        "square_lattice_2d": "sq",
        "bottleneck_lattice": "bottle",
        "clustered_lattice": "cluster",
    }[medium_type]
    return tuple(f"{prefix}_{index}" for index in range(n_sites))


def build_medium_definition(
    *,
    medium_type: str,
    coupling_law: str,
    length_scale: float,
    disorder_strength_hz: float,
    site_energy_profile: str,
    coordinates: np.ndarray | None = None,
    seed: int | None = None,
    n_sites: int | None = None,
    n_rows: int | None = None,
    n_cols: int | None = None,
    n_cols_left: int | None = None,
    n_cols_right: int | None = None,
    cluster_size: int | None = None,
    gradient_strength_hz: float = 0.0,
    decay_length: float = 1.5,
    power_law_exponent: float = 3.0,
    cutoff_radius: float | None = None,
) -> MediumDefinition:
    if coordinates is None:
        coordinates = build_medium_coordinates(
            medium_type=medium_type,
            n_sites=n_sites,
            n_rows=n_rows,
            n_cols=n_cols,
            n_cols_left=n_cols_left,
            n_cols_right=n_cols_right,
            cluster_size=cluster_size,
            length_scale=length_scale,
        )
    else:
        coordinates = np.asarray(coordinates, dtype=float)
        if coordinates.ndim != 2 or coordinates.shape[0] < 2:
            raise ValueError("coordinates must be a 2D array with at least two sites")
    adjacency = build_coupling_adjacency(
        coordinates,
        medium_type=medium_type,
        coupling_law=coupling_law,
        length_scale=length_scale,
        decay_length=decay_length,
        power_law_exponent=power_law_exponent,
        cutoff_radius=cutoff_radius,
    )
    energies = build_site_energies(
        coordinates,
        site_energy_profile=site_energy_profile,
        disorder_strength_hz=disorder_strength_hz,
        seed=seed,
        gradient_strength_hz=gradient_strength_hz,
    )
    labels = medium_labels(medium_type, coordinates.shape[0])
    metadata: dict[str, float | int | str] = {
        "medium_type": medium_type,
        "n_sites": int(coordinates.shape[0]),
        "length_scale": float(length_scale),
        "coupling_law": coupling_law,
        "site_energy_profile": site_energy_profile,
        "disorder_strength_hz": float(disorder_strength_hz),
    }
    if n_rows is not None:
        metadata["n_rows"] = int(n_rows)
    if n_cols is not None:
        metadata["n_cols"] = int(n_cols)
    if n_cols_left is not None:
        metadata["n_cols_left"] = int(n_cols_left)
    if n_cols_right is not None:
        metadata["n_cols_right"] = int(n_cols_right)
    if cluster_size is not None:
        metadata["cluster_size"] = int(cluster_size)
    return MediumDefinition(
        medium_type=medium_type,
        adjacency=adjacency,
        coordinates=coordinates,
        site_energies_hz=energies,
        labels=labels,
        metadata=metadata,
    )
