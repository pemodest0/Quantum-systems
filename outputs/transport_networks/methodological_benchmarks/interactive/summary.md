# Transport methodological benchmarks

Generated at UTC: 2026-04-21T09:40:41.695114+00:00
Profile: `interactive`

## What was benchmarked

- Closed coherent quantum-walk topology control.
- Trap/target placement control.
- Dephasing-assisted transport control.
- Dynamic graph-family classification control.
- Edge-weight model sensitivity control.

## Main measured numbers

- Open dynamic signatures: 1656.
- Families: barabasi_albert_scale_free, bottleneck, chain, clustered, complete, erdos_renyi, modular_two_community, random_geometric, ring, square_lattice_2d, star, watts_strogatz_small_world.
- Edge models: degree_normalized, exponential_distance, power_law_distance, unweighted.
- Largest dephasing gain: 0.325 in `random_geometric` / `near` / `exponential_distance`.
- Useful dephasing candidates: 730.
- Max target-position spread: 0.737.
- Family classification, dynamic only: 0.540.
- Family classification, topology only: 0.553.
- Family classification, dynamic + topology: 0.633.
- Majority baseline: 0.135.

## Methodological verdict

- Numerics pass: True.
- Target placement candidate: True.
- Dephasing assistance candidate: True.
- Dynamic classification above baseline: True.
- Dynamics adds beyond topology in this run: True.

## Important limitation

This benchmark checks methodological coherence and reproduces qualitative expectations. It is not yet a final physics claim; article-level claims require the confirm profile and local refinement of the strongest cases.

## Classification controls

```json
{
  "dynamic_only_family": {
    "accuracy": 0.540084388185654,
    "baseline_accuracy": 0.1350210970464135,
    "labels": [
      "barabasi_albert_scale_free",
      "bottleneck",
      "chain",
      "clustered",
      "complete",
      "erdos_renyi",
      "modular_two_community",
      "random_geometric",
      "ring",
      "square_lattice_2d",
      "star",
      "watts_strogatz_small_world"
    ],
    "top_features": [
      {
        "feature": "best_final_front_width",
        "importance": 1.5094251097821962
      },
      {
        "feature": "best_final_msd",
        "importance": 0.8252545225057903
      },
      {
        "feature": "best_sink_hitting_time_filled",
        "importance": 0.530893409585651
      },
      {
        "feature": "best_transfer_time_filled",
        "importance": 0.434316386607702
      },
      {
        "feature": "best_network_population",
        "importance": 0.39100775986013453
      }
    ]
  },
  "topology_only_family": {
    "accuracy": 0.5527426160337553,
    "baseline_accuracy": 0.1350210970464135,
    "labels": [
      "barabasi_albert_scale_free",
      "bottleneck",
      "chain",
      "clustered",
      "complete",
      "erdos_renyi",
      "modular_two_community",
      "random_geometric",
      "ring",
      "square_lattice_2d",
      "star",
      "watts_strogatz_small_world"
    ],
    "top_features": [
      {
        "feature": "topology_std_degree",
        "importance": 1.0484871788984589
      },
      {
        "feature": "topology_modularity_approx",
        "importance": 0.9786252507014167
      },
      {
        "feature": "topology_spectral_degeneracy_approx",
        "importance": 0.9404005269173754
      },
      {
        "feature": "topology_spectral_gap",
        "importance": 0.7319338602535361
      },
      {
        "feature": "topology_initial_degree",
        "importance": 0.6769630224383033
      }
    ]
  },
  "combined_family": {
    "accuracy": 0.6329113924050633,
    "baseline_accuracy": 0.1350210970464135,
    "labels": [
      "barabasi_albert_scale_free",
      "bottleneck",
      "chain",
      "clustered",
      "complete",
      "erdos_renyi",
      "modular_two_community",
      "random_geometric",
      "ring",
      "square_lattice_2d",
      "star",
      "watts_strogatz_small_world"
    ],
    "top_features": [
      {
        "feature": "best_final_front_width",
        "importance": 0.8148461058619038
      },
      {
        "feature": "topology_modularity_approx",
        "importance": 0.8070445351310785
      },
      {
        "feature": "topology_std_degree",
        "importance": 0.6994612432458897
      },
      {
        "feature": "topology_spectral_degeneracy_approx",
        "importance": 0.6992354250520411
      },
      {
        "feature": "topology_initial_degree",
        "importance": 0.5660330404679347
      }
    ]
  },
  "dynamic_only_edge_model": {
    "accuracy": 0.48588709677419356,
    "baseline_accuracy": 0.4798387096774194,
    "labels": [
      "degree_normalized",
      "exponential_distance",
      "power_law_distance",
      "unweighted"
    ],
    "top_features": [
      {
        "feature": "best_final_front_width",
        "importance": 0.7697017452464512
      },
      {
        "feature": "best_participation_ratio",
        "importance": 0.6837286142705684
      },
      {
        "feature": "best_mean_coherence_l1",
        "importance": 0.6347990340442348
      },
      {
        "feature": "best_ipr",
        "importance": 0.5307014308359692
      },
      {
        "feature": "regime_confidence",
        "importance": 0.49095748886108587
      }
    ]
  }
}
```
