# Parameter-Space And Combinatorial Explosion Analysis

Generated at UTC: 2026-04-23T05:13:57.359554+00:00

## What Explodes

The dominant multiplier is not one variable alone. It is:

`families x N values x graph realizations x target choices x disorder values x disorder seeds x dephasing values`.

For each final record, the quantum model runs a full dephasing scan. Therefore, adding one extra value of `gamma/J` multiplies every graph/target/disorder case.

## Main Counts

| Campaign/profile | Records | Quantum simulations | Classical controls | Graph instances |
|---|---:|---:|---:|---:|
| Atlas evidence prep | 1032 | 7224 | 1032 | 22 |
| Atlas strong | 50000 | 400000 | 50000 | 207 |
| Atlas intense | 217536 | 3263040 | 217536 | 356 |
| Paper validation profile | 810 | 3240 | 810 | 36 |

## Strong Atlas: Families That Dominate Record Count

- `modular_two_community`: 9520 final records before multiplying interpretation/reporting.
- `watts_strogatz_small_world`: 9360 final records before multiplying interpretation/reporting.
- `erdos_renyi`: 9040 final records before multiplying interpretation/reporting.
- `barabasi_albert_scale_free`: 8400 final records before multiplying interpretation/reporting.
- `random_geometric`: 8400 final records before multiplying interpretation/reporting.

## Strong Atlas: Families That Dominate Estimated Compute Cost

- `watts_strogatz_small_world`: relative cost units `1.298e+11`.
- `random_geometric`: relative cost units `1.181e+11`.
- `modular_two_community`: relative cost units `1.163e+11`.
- `barabasi_albert_scale_free`: relative cost units `1.098e+11`.
- `erdos_renyi`: relative cost units `8.985e+10`.

## Practical Reading

- Random families are expensive because each size has many independent graph realizations.
- Gamma/dephasing grids are expensive because every point requires a full Lindblad time evolution.
- Disorder seeds are expensive but scientifically important because they give uncertainty and prevent one lucky disorder draw from becoming a claim.
- Complete graphs are dense, so each simulation is structurally heavier, but they do not dominate total count because they have only one deterministic instance per size.
- Fractals are not the biggest combinatorial load yet; they become expensive if we add many sizes and seeds.

## Where To Cut First If The PC Is Busy

1. Keep all families, but reduce random graph realizations before reducing physics grids.
2. Keep `gamma/J = 0` and the suspected optimum window, but remove redundant high-gamma points unless testing the ceiling.
3. Keep disorder seeds for candidate claims; reduce seeds only for exploratory scans.
4. Do not run all target styles everywhere. Use `near/far` for atlas, then controlled target sweeps only where target position matters.
5. Move strong atlas and confirm profiles to the Mac; keep evidence-prep and paper-specific refinements on this PC.

## Outputs

- `parameter_cost_summary.csv`: campaign-level counts.
- `family_cost_breakdown.csv`: family/size/realization-level counts and graph density.
- `combinatorial_factors.csv`: raw multipliers for each profile.
- `auxiliary_benchmark_costs.csv`: Coates, Anderson and Manzano auxiliary benchmark counts.
- `combinatorial_explosion_dashboard.png`: visual summary.
