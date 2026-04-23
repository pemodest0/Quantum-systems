# Methodological benchmark protocol

## Scientific question

Can the time evolution of one excitation identify the network family and the physical transport regime?

## Controls

1. Closed coherent walk: sink, loss, dephasing, and disorder are set to zero. This checks topology-dependent spreading without open-system channels.
2. Trap/target placement: dephasing and disorder are set to zero, and only the target position is changed.
3. Dephasing-assisted transport: static disorder is fixed per seed, and dephasing is scanned against the zero-dephasing control.
4. Dynamic classification: dynamic signatures are classified and compared against topology-only and majority-baseline controls.
5. Edge-weight sensitivity: representative graph families are rerun with alternative edge-weight laws.

## Normalizations

- Time is reported in units of 1/J, where J is the coherent coupling scale.
- Disorder means local site-energy irregularity divided by J.
- Dephasing means phase-scrambling rate divided by J.
- Target arrival means accumulated population in the successful arrival channel.
- Entropy, purity, participation ratio, and IPR are computed on the graph-only normalized state unless otherwise stated by the simulator payload.

## Acceptance rules

- Numerical validity requires trace and population closure errors below 1e-8 and minimum eigenvalue above -1e-7.
- A dephasing-assistance candidate requires gain >= 0.05 and best dephasing > 0.
- A target-placement candidate requires target-position spread >= 0.05 inside the same graph instance.
- A dynamic-classification candidate must beat the majority baseline.
- No run is interpreted as a final physics claim unless it survives a larger ensemble confirmation.

## Profile used

```json
{
  "profile": "interactive",
  "families": [
    "chain",
    "ring",
    "complete",
    "star",
    "erdos_renyi",
    "watts_strogatz_small_world",
    "barabasi_albert_scale_free",
    "modular_two_community",
    "random_geometric",
    "square_lattice_2d",
    "bottleneck",
    "clustered"
  ],
  "edge_models_main": [
    "unweighted"
  ],
  "edge_models_sensitivity": [
    "unweighted",
    "degree_normalized",
    "exponential_distance",
    "power_law_distance"
  ],
  "edge_sensitivity_families": [
    "chain",
    "ring",
    "modular_two_community",
    "random_geometric"
  ],
  "n_sites_values": [
    8
  ],
  "graph_realizations": 3,
  "deterministic_graph_realizations": 1,
  "disorder_seeds": [
    3,
    5,
    7
  ],
  "graph_seed_base": 4200,
  "disorder_strength_over_coupling": [
    0.0,
    0.6,
    1.0
  ],
  "dephasing_over_coupling": [
    0.0,
    0.05,
    0.2,
    0.6
  ],
  "target_styles": [
    "near",
    "far",
    "high_centrality",
    "low_centrality"
  ],
  "t_final_closed": 10.0,
  "t_final_open": 12.0,
  "n_time_samples": 120,
  "coupling_hz": 1.0,
  "sink_rate_hz": 0.65,
  "loss_rate_hz": 0.02
}
```
