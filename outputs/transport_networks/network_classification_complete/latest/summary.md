# Network Classification Complete Pack

## Scientific Question

Can we recognize the network family by looking at the open-transport dynamics?

## Plain Reading

- `dynamic_only`: uses only transport behavior, such as target arrival, coherence, entropy, and participation.
- `topology_only`: uses graph numbers directly, such as degree, distance, and spectral measures.
- `classical_only`: uses a classical rate-walk control.
- `combined`: uses dynamic signatures plus topology numbers.
- `group split`: keeps the same graph instance out of both train and test, avoiding leakage.

## Main Result

- Dynamic-only accuracy: 0.415.
- Topology-only accuracy: 0.558.
- Classical-only accuracy: 0.176.
- Combined accuracy: 0.615.
- Combined baseline: 0.133.

## Interpretation

The classification claim is meaningful only because the split is by graph instance, not by row. If row-level splitting were used, nearby parameter rows from the same graph could leak into train and test.

## Per-Family Reading

| Family | Records | Mean arrival | Mean gain | First-split accuracy |
|---|---:|---:|---:|---:|
| `barabasi_albert_scale_free` | 54 | 0.414 | 0.108 | 0.889 |
| `bottleneck` | 54 | 0.466 | 0.031 | 0.000 |
| `chain` | 54 | 0.450 | 0.051 | 0.389 |
| `clustered` | 54 | 0.465 | 0.036 | 0.000 |
| `complete` | 54 | 0.194 | 0.098 | 1.000 |
| `erdos_renyi` | 54 | 0.382 | 0.066 | 0.667 |
| `modular_two_community` | 108 | 0.300 | 0.057 | 0.500 |
| `random_geometric` | 108 | 0.341 | 0.057 | 0.167 |
| `ring` | 108 | 0.465 | 0.059 | 1.000 |
| `square_lattice_2d` | 54 | 0.414 | 0.095 | 0.667 |
| `star` | 54 | 0.292 | 0.175 | 1.000 |
| `watts_strogatz_small_world` | 54 | 0.425 | 0.059 | 0.778 |

## Size Generalization

The size-generalization block trains on N=8 and tests on N=10 or N=12. If this fails, the fingerprint may be size-specific rather than family-specific.

Available splits: train_N8_test_N10, train_N8_test_N12.

## Next Action

Use the confusion matrix to pick the most confused family pair and design one focused campaign for that pair.
