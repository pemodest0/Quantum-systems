from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MaterialFamilyTemplate:
    name: str
    plain_meaning: str
    medium_type: str
    default_medium_block: dict[str, object]
    recommended_knobs: tuple[str, ...]


def built_in_material_families() -> dict[str, MaterialFamilyTemplate]:
    return {
        "molecular_wire_chain": MaterialFamilyTemplate(
            name="molecular_wire_chain",
            plain_meaning="A short effective molecular wire where the excitation moves mainly along one direction.",
            medium_type="chain_1d",
            default_medium_block={
                "medium_type": "chain_1d",
                "n_sites": 10,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 4.5,
            },
            recommended_knobs=("disorder_strength_over_coupling", "dephasing_over_coupling", "sink_rate_over_coupling"),
        ),
        "ring_aggregate": MaterialFamilyTemplate(
            name="ring_aggregate",
            plain_meaning="A small ring-like aggregate with competing coherent paths to the target.",
            medium_type="ring",
            default_medium_block={
                "medium_type": "ring",
                "n_sites": 8,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 0.0,
            },
            recommended_knobs=("disorder_strength_over_coupling", "dephasing_over_coupling", "trap_site"),
        ),
        "disordered_2d_excitonic_sheet": MaterialFamilyTemplate(
            name="disordered_2d_excitonic_sheet",
            plain_meaning="A small two-dimensional sheet with several alternate paths across the medium.",
            medium_type="square_lattice_2d",
            default_medium_block={
                "medium_type": "square_lattice_2d",
                "n_rows": 4,
                "n_cols": 4,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 1.5,
            },
            recommended_knobs=("disorder_strength_over_coupling", "dephasing_over_coupling", "loss_rate_over_coupling"),
        ),
        "bottleneck_medium": MaterialFamilyTemplate(
            name="bottleneck_medium",
            plain_meaning="A medium with two regions connected by a narrow bridge that can limit transport.",
            medium_type="bottleneck_lattice",
            default_medium_block={
                "medium_type": "bottleneck_lattice",
                "n_rows": 3,
                "n_cols_left": 2,
                "n_cols_right": 2,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 1.5,
            },
            recommended_knobs=("disorder_strength_over_coupling", "dephasing_over_coupling", "cutoff_radius"),
        ),
        "clustered_medium": MaterialFamilyTemplate(
            name="clustered_medium",
            plain_meaning="A medium formed by two small clusters weakly connected by a single bridge.",
            medium_type="clustered_lattice",
            default_medium_block={
                "medium_type": "clustered_lattice",
                "cluster_size": 3,
                "length_scale": 1.0,
                "coupling_law": "nearest_neighbor",
                "site_energy_profile": "static_disorder",
                "sink_definition": {"mode": "single_site", "site_index": 0},
                "loss_definition": {"mode": "uniform_local_loss"},
                "interface_axis": "x",
                "interface_position": 2.0,
            },
            recommended_knobs=("disorder_strength_over_coupling", "dephasing_over_coupling", "bridge_strength"),
        ),
    }


def material_family_payload() -> dict[str, object]:
    return {name: asdict(template) for name, template in built_in_material_families().items()}
