# Transport methodological benchmarks

Generated at UTC: 2026-04-21T09:20:04.123864+00:00
Profile: `smoke`

## What was benchmarked

- Closed coherent quantum-walk topology control.
- Trap/target placement control.
- Dephasing-assisted transport control.
- Dynamic graph-family classification control.
- Edge-weight model sensitivity control.

## Main measured numbers

- Open dynamic signatures: 64.
- Families: chain, complete, ring, star.
- Edge models: degree_normalized, unweighted.
- Largest dephasing gain: 0.211 in `star` / `near` / `degree_normalized`.
- Useful dephasing candidates: 46.
- Max target-position spread: 0.396.
- Family classification, dynamic only: 1.000.
- Family classification, topology only: 1.000.
- Family classification, dynamic + topology: 1.000.
- Majority baseline: 0.250.

## Methodological verdict

- Numerics pass: True.
- Target placement candidate: True.
- Dephasing assistance candidate: True.
- Dynamic classification above baseline: True.
- Dynamics adds beyond topology in this run: False.

## Important limitation

This benchmark checks methodological coherence and reproduces qualitative expectations. It is not yet a final physics claim; article-level claims require the confirm profile and local refinement of the strongest cases.

## Classification controls

```json
{
  "dynamic_only_family": {
    "accuracy": 1.0,
    "baseline_accuracy": 0.25,
    "labels": [
      "chain",
      "complete",
      "ring",
      "star"
    ],
    "top_features": [
      {
        "feature": "best_final_front_width",
        "importance": 1.8994094738827245
      },
      {
        "feature": "best_sink_hitting_time_filled",
        "importance": 0.9202497705676617
      },
      {
        "feature": "best_final_msd",
        "importance": 0.7200071213018995
      },
      {
        "feature": "best_network_population",
        "importance": 0.5998835598956038
      },
      {
        "feature": "mean_arrival_over_dephasing",
        "importance": 0.5873980728938263
      }
    ]
  },
  "topology_only_family": {
    "accuracy": 1.0,
    "baseline_accuracy": 0.25,
    "labels": [
      "chain",
      "complete",
      "ring",
      "star"
    ],
    "top_features": [
      {
        "feature": "topology_std_degree",
        "importance": 1.1864940880364174
      },
      {
        "feature": "topology_spectral_degeneracy_approx",
        "importance": 0.974674304690673
      },
      {
        "feature": "topology_modularity_approx",
        "importance": 0.6506010831065832
      },
      {
        "feature": "topology_initial_degree",
        "importance": 0.5172375957443778
      },
      {
        "feature": "topology_spectral_gap",
        "importance": 0.40166707641921084
      }
    ]
  },
  "combined_family": {
    "accuracy": 1.0,
    "baseline_accuracy": 0.25,
    "labels": [
      "chain",
      "complete",
      "ring",
      "star"
    ],
    "top_features": [
      {
        "feature": "topology_std_degree",
        "importance": 0.5544846376855047
      },
      {
        "feature": "best_final_front_width",
        "importance": 0.5176310443202494
      },
      {
        "feature": "best_sink_hitting_time_filled",
        "importance": 0.43732282585112064
      },
      {
        "feature": "best_final_msd",
        "importance": 0.43480710503300823
      },
      {
        "feature": "topology_spectral_degeneracy_approx",
        "importance": 0.37393512267472545
      }
    ]
  },
  "dynamic_only_edge_model": {
    "accuracy": 0.4,
    "baseline_accuracy": 0.5,
    "labels": [
      "degree_normalized",
      "unweighted"
    ],
    "top_features": [
      {
        "feature": "best_final_msd",
        "importance": 4.25292779039636e-15
      },
      {
        "feature": "best_final_front_width",
        "importance": 2.2098689862417443e-15
      },
      {
        "feature": "best_network_population",
        "importance": 2.033048770103207e-15
      },
      {
        "feature": "best_sink_hitting_time_filled",
        "importance": 1.641809053338324e-15
      },
      {
        "feature": "dephasing_gain",
        "importance": 1.641790692653739e-15
      }
    ]
  }
}
```
