from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class LiteratureExpectation:
    expected_transport_trend: str
    expected_role_of_disorder: str
    expected_role_of_phase_scrambling: str
    expected_failure_mode: str


@dataclass(frozen=True)
class MediumSpec:
    medium_type: str
    length_scale: float
    coupling_law: str
    site_energy_profile: str
    sink_definition: dict[str, object]
    loss_definition: dict[str, object]
    coordinates: tuple[tuple[float, ...], ...] | None
    n_sites: int | None
    n_rows: int | None
    n_cols: int | None
    n_cols_left: int | None
    n_cols_right: int | None
    cluster_size: int | None
    gradient_strength_hz: float
    decay_length: float
    power_law_exponent: float
    cutoff_radius: float | None
    interface_axis: str | None
    interface_position: float | None


@dataclass(frozen=True)
class MediumCampaignScenario:
    name: str
    coupling_hz: float
    sink_rate_hz: float
    loss_rate_hz: float
    initial_site: int
    trap_site: int
    medium: MediumSpec
    literature_expectation: LiteratureExpectation


@dataclass(frozen=True)
class MediumCampaignConfig:
    study_name: str
    output_subdir: str
    t_final: float
    n_time_samples: int
    sink_hit_threshold: float
    transfer_threshold: float
    disorder_strength_over_coupling: np.ndarray
    dephasing_over_coupling: np.ndarray
    ensemble_seeds: tuple[int, ...]
    scenarios: tuple[MediumCampaignScenario, ...]


def load_medium_campaign_config(path: str | Path) -> MediumCampaignConfig:
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))

    scenarios: list[MediumCampaignScenario] = []
    for block in raw["scenarios"]:
        medium_raw = block["medium"]
        expectation_raw = block["literature_expectation"]
        medium = MediumSpec(
            medium_type=str(medium_raw["medium_type"]),
            length_scale=float(medium_raw.get("length_scale", 1.0)),
            coupling_law=str(medium_raw.get("coupling_law", "nearest_neighbor")),
            site_energy_profile=str(medium_raw.get("site_energy_profile", "uniform")),
            sink_definition=dict(medium_raw.get("sink_definition", {"mode": "single_site"})),
            loss_definition=dict(medium_raw.get("loss_definition", {"mode": "uniform_local_loss"})),
            coordinates=tuple(tuple(float(v) for v in row) for row in medium_raw["coordinates"]) if "coordinates" in medium_raw else None,
            n_sites=int(medium_raw["n_sites"]) if "n_sites" in medium_raw else None,
            n_rows=int(medium_raw["n_rows"]) if "n_rows" in medium_raw else None,
            n_cols=int(medium_raw["n_cols"]) if "n_cols" in medium_raw else None,
            n_cols_left=int(medium_raw["n_cols_left"]) if "n_cols_left" in medium_raw else None,
            n_cols_right=int(medium_raw["n_cols_right"]) if "n_cols_right" in medium_raw else None,
            cluster_size=int(medium_raw["cluster_size"]) if "cluster_size" in medium_raw else None,
            gradient_strength_hz=float(medium_raw.get("gradient_strength_hz", 0.0)),
            decay_length=float(medium_raw.get("decay_length", 1.5)),
            power_law_exponent=float(medium_raw.get("power_law_exponent", 3.0)),
            cutoff_radius=float(medium_raw["cutoff_radius"]) if "cutoff_radius" in medium_raw else None,
            interface_axis=str(medium_raw["interface_axis"]) if "interface_axis" in medium_raw else None,
            interface_position=float(medium_raw["interface_position"]) if "interface_position" in medium_raw else None,
        )
        expectation = LiteratureExpectation(
            expected_transport_trend=str(expectation_raw["expected_transport_trend"]),
            expected_role_of_disorder=str(expectation_raw["expected_role_of_disorder"]),
            expected_role_of_phase_scrambling=str(expectation_raw["expected_role_of_phase_scrambling"]),
            expected_failure_mode=str(expectation_raw["expected_failure_mode"]),
        )
        scenarios.append(
            MediumCampaignScenario(
                name=str(block["name"]),
                coupling_hz=float(block["coupling_hz"]),
                sink_rate_hz=float(block["sink_rate_hz"]),
                loss_rate_hz=float(block["loss_rate_hz"]),
                initial_site=int(block["initial_site"]),
                trap_site=int(block["trap_site"]),
                medium=medium,
                literature_expectation=expectation,
            )
        )

    return MediumCampaignConfig(
        study_name=str(raw["study_name"]),
        output_subdir=str(raw["output_subdir"]),
        t_final=float(raw["time_grid"]["t_final"]),
        n_time_samples=int(raw["time_grid"]["n_samples"]),
        sink_hit_threshold=float(raw.get("thresholds", {}).get("sink_hit_threshold", 0.1)),
        transfer_threshold=float(raw.get("thresholds", {}).get("transfer_threshold", 0.5)),
        disorder_strength_over_coupling=np.asarray(raw["sweep"]["disorder_strength_over_coupling"], dtype=float),
        dephasing_over_coupling=np.asarray(raw["sweep"]["dephasing_over_coupling"], dtype=float),
        ensemble_seeds=tuple(int(seed) for seed in raw["ensemble_seeds"]),
        scenarios=tuple(scenarios),
    )
