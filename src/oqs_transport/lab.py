from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .networks import (
    chain_adjacency,
    complete_adjacency,
    ring_adjacency,
    static_disorder_energies,
)

SUPPORTED_TOPOLOGIES = ("chain", "ring", "complete")


@dataclass(frozen=True)
class TransportScenarioConfig:
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


@dataclass(frozen=True)
class TransportLabConfig:
    study_name: str
    output_subdir: str
    t_final: float
    n_time_samples: int
    animation_stride: int
    animation_fps: int
    dephasing_rates_hz: np.ndarray
    scenarios: tuple[TransportScenarioConfig, ...]


def adjacency_for_topology(topology: str, n_sites: int) -> np.ndarray:
    if topology == "chain":
        return chain_adjacency(n_sites)
    if topology == "ring":
        return ring_adjacency(n_sites)
    if topology == "complete":
        return complete_adjacency(n_sites)
    raise ValueError(f"unsupported topology: {topology}")


def site_energies_for_scenario(scenario: TransportScenarioConfig) -> np.ndarray:
    if scenario.disorder_strength_hz == 0.0:
        return np.zeros(scenario.n_sites, dtype=float)
    return static_disorder_energies(
        scenario.n_sites,
        disorder_strength=scenario.disorder_strength_hz,
        seed=scenario.seed,
    )


def classify_transport_regime(best_idx: int, n_rates: int) -> str:
    if best_idx == 0:
        return "coherent"
    if best_idx == n_rates - 1:
        return "strongly_dissipative"
    return "intermediate"


def load_transport_lab_config(path: str | Path) -> TransportLabConfig:
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))

    study_name = str(raw["study_name"]).strip()
    output_subdir = str(raw["output_subdir"]).strip()
    time_grid = raw["time_grid"]
    t_final = float(time_grid["t_final"])
    n_time_samples = int(time_grid["n_samples"])
    visualization = raw.get("visualization", {})
    animation_stride = int(visualization.get("animation_stride", 15))
    animation_fps = int(visualization.get("animation_fps", 12))
    dephasing_rates = np.asarray(raw["dephasing_rates_hz"], dtype=float)

    if not study_name:
        raise ValueError("study_name must be non-empty")
    if not output_subdir:
        raise ValueError("output_subdir must be non-empty")
    if t_final <= 0.0:
        raise ValueError("t_final must be positive")
    if n_time_samples < 2:
        raise ValueError("n_samples must be at least 2")
    if animation_stride < 1:
        raise ValueError("animation_stride must be at least 1")
    if animation_fps < 1:
        raise ValueError("animation_fps must be at least 1")
    if dephasing_rates.ndim != 1 or dephasing_rates.size == 0:
        raise ValueError("dephasing_rates_hz must be a non-empty 1D array")
    if np.any(dephasing_rates < 0.0):
        raise ValueError("dephasing rates must be non-negative")

    seen_names: set[str] = set()
    scenarios: list[TransportScenarioConfig] = []
    for block in raw["scenarios"]:
        scenario = TransportScenarioConfig(
            name=str(block["name"]).strip(),
            topology=str(block["topology"]).strip(),
            n_sites=int(block["n_sites"]),
            coupling_hz=float(block["coupling_hz"]),
            sink_rate_hz=float(block["sink_rate_hz"]),
            loss_rate_hz=float(block["loss_rate_hz"]),
            initial_site=int(block["initial_site"]),
            trap_site=int(block["trap_site"]),
            disorder_strength_hz=float(block["disorder_strength_hz"]),
            seed=int(block["seed"]),
        )
        _validate_scenario_config(scenario)
        if scenario.name in seen_names:
            raise ValueError(f"duplicate scenario name: {scenario.name}")
        seen_names.add(scenario.name)
        scenarios.append(scenario)

    return TransportLabConfig(
        study_name=study_name,
        output_subdir=output_subdir,
        t_final=t_final,
        n_time_samples=n_time_samples,
        animation_stride=animation_stride,
        animation_fps=animation_fps,
        dephasing_rates_hz=dephasing_rates,
        scenarios=tuple(scenarios),
    )


def _validate_scenario_config(scenario: TransportScenarioConfig) -> None:
    if not scenario.name:
        raise ValueError("scenario name must be non-empty")
    if scenario.topology not in SUPPORTED_TOPOLOGIES:
        raise ValueError(f"unsupported topology: {scenario.topology}")
    if scenario.n_sites < 2:
        raise ValueError("n_sites must be at least 2")
    if scenario.coupling_hz <= 0.0:
        raise ValueError("coupling_hz must be positive")
    if scenario.sink_rate_hz < 0.0:
        raise ValueError("sink_rate_hz must be non-negative")
    if scenario.loss_rate_hz < 0.0:
        raise ValueError("loss_rate_hz must be non-negative")
    if scenario.disorder_strength_hz < 0.0:
        raise ValueError("disorder_strength_hz must be non-negative")
    if scenario.initial_site < 0 or scenario.initial_site >= scenario.n_sites:
        raise ValueError("initial_site out of range")
    if scenario.trap_site < 0 or scenario.trap_site >= scenario.n_sites:
        raise ValueError("trap_site out of range")
